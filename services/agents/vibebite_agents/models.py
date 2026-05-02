"""LLM client wrapper.

A thin shim that node code can import without caring whether the real
Gemini / OpenAI client or the local stub is in use.

Provider selection (env-driven, with graceful fallback to the stub):

  * If ``VIBEBITE_USE_STUBS=1`` is set, the stub LLM is *always* used.
  * Else ``LLM_PROVIDER`` (default: ``gemini``) picks the backend:

      - ``gemini``  : real Google Gemini client (``GEMINI_API_KEY`` required;
                      missing key falls back to the stub).
      - ``openai``  : OpenAI client (currently a stub placeholder; missing key
                      or unimplemented backend falls back to the stub).
      - ``stub``    : explicit stub.

  * Any other value falls back to the stub.

Public surface (mirrors what ``parse_preferences`` and ``explain_candidates``
will call)::

    llm = get_llm()
    result = await llm.chat_completion(messages, response_model=GroupConstraints)

``messages`` follows the OpenAI chat shape: ``[{"role": "user", "content": "..."}]``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Iterable, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from .clients.llm_stub import stub_chat_completion

try:  # structlog is in deps; keep an import guard so import never explodes.
    import structlog

    _log = structlog.get_logger(__name__)
except Exception:  # noqa: BLE001
    _log = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)
MessagesType = Union[str, Iterable[dict[str, Any]]]


class LLMError(RuntimeError):
    """Raised when a real LLM call fails (network, auth, parse, etc.)."""


class StubLLM:
    """Drop-in stand-in for the real LLM client.

    The method is `async def` so node code can `await` uniformly across stub
    and real backends; the underlying implementation is sync but returning
    from an `async def` produces a coroutine the caller can await.
    """

    using_stub = True

    async def chat_completion(self, messages: MessagesType, response_model: Type[T]) -> T:
        return stub_chat_completion(messages, response_model)


class OpenAILLM:
    """Real OpenAI-backed LLM. Implementation lands later.

    Kept as a clearly-typed placeholder so downstream code can reference the
    eventual class name without a future rename breaking imports.
    """

    using_stub = False

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def chat_completion(self, messages: MessagesType, response_model: Type[T]) -> T:
        raise NotImplementedError(
            "Real OpenAI client not yet implemented. Set VIBEBITE_USE_STUBS=1 or "
            "LLM_PROVIDER=stub to use the StubLLM in the meantime."
        )


def _messages_to_gemini_prompt(messages: MessagesType) -> str:
    """Flatten an OpenAI-style messages list into a single prompt string.

    Gemini's ``generate_content`` accepts a single string for one-shot calls,
    which matches our usage (system + user). System messages are prefixed with
    ``[system]`` so the model still sees the framing.
    """
    if isinstance(messages, str):
        return messages
    parts: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role", "user")).lower()
        content = m.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                chunk.get("text", "")
                for chunk in content
                if isinstance(chunk, dict) and isinstance(chunk.get("text"), str)
            )
        else:
            text = str(content or "")
        if not text:
            continue
        if role == "system":
            parts.append(f"[system]\n{text}")
        elif role == "assistant":
            parts.append(f"[assistant]\n{text}")
        else:
            parts.append(f"[user]\n{text}")
    return "\n\n".join(parts)


class GeminiLLM:
    """Real Google Gemini-backed LLM with Pydantic structured output.

    Uses the ``google-genai`` SDK's native structured-output support: we hand
    Gemini the response Pydantic model class as ``response_schema`` and read
    the validated instance back from ``response.parsed``.
    """

    using_stub = False

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        # Imported lazily so pure-stub setups don't pay the import cost.
        from google import genai  # type: ignore

        self._api_key = api_key
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def chat_completion(
        self, messages: MessagesType, response_model: Type[T]
    ) -> T:
        from google.genai import types  # type: ignore

        prompt = _messages_to_gemini_prompt(messages)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_model,
        )

        def _call() -> Any:
            return self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )

        try:
            response = await asyncio.to_thread(_call)
        except Exception as exc:  # noqa: BLE001
            try:
                _log.error("gemini_call_failed", error=str(exc), model=self._model)
            except Exception:  # noqa: BLE001
                print(f"[GeminiLLM] call failed: {exc!r}")
            raise LLMError(f"Gemini call failed: {exc}") from exc

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, response_model):
            return parsed
        # Fallback: hand-validate raw JSON text if SDK didn't pre-parse.
        text = getattr(response, "text", None)
        if text:
            try:
                return response_model.model_validate_json(text)
            except Exception as exc:  # noqa: BLE001
                raise LLMError(
                    f"Gemini returned text but it failed schema validation: {exc}"
                ) from exc
        raise LLMError("Gemini returned no parsed content and no text fallback.")


class ResilientLLM:
    """Wraps a primary LLM and falls back to a backup on quota / transient errors.

    Today's primary is Gemini, the backup is StubLLM. On a free-tier quota
    exhaustion (HTTP 429 / RESOURCE_EXHAUSTED) we don't want the entire graph
    to crash mid-mission, so we degrade silently to the stub and log loudly
    via structlog so the audit trail records the fallback.
    """

    def __init__(self, primary: Any, backup: Any) -> None:
        self._primary = primary
        self._backup = backup

    async def chat_completion(
        self, messages: MessagesType, response_model: Type[T]
    ) -> T:
        try:
            return await self._primary.chat_completion(messages, response_model)
        except LLMError as exc:
            msg = str(exc).lower()
            transient = any(
                marker in msg
                for marker in (
                    "429",
                    "resource_exhausted",
                    "quota",
                    "rate limit",
                    "503",
                    "timeout",
                )
            )
            if not transient:
                raise
            try:
                _log.warning(
                    "llm_fallback_to_stub",
                    primary=type(self._primary).__name__,
                    reason=str(exc)[:200],
                )
            except Exception:  # noqa: BLE001
                print(f"[ResilientLLM] falling back to stub: {exc}")
            return await self._backup.chat_completion(messages, response_model)


def get_llm() -> Any:
    """Return the configured LLM client.

    Reads ``LLM_PROVIDER``, ``GEMINI_API_KEY``, ``GEMINI_MODEL``,
    ``OPENAI_API_KEY``, and ``VIBEBITE_USE_STUBS`` from the environment so
    node code stays a one-liner::

        llm = get_llm()

    Real providers are wrapped in ``ResilientLLM`` so a free-tier quota wall
    transparently degrades to the stub instead of breaking the graph.
    Falls back to ``StubLLM`` whenever the requested provider lacks a key.
    """
    if os.getenv("VIBEBITE_USE_STUBS") == "1":
        return StubLLM()

    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return StubLLM()
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        return ResilientLLM(GeminiLLM(api_key=key, model=model), StubLLM())

    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return StubLLM()
        # Real OpenAI client not yet implemented; stub-fallback for safety.
        return StubLLM()

    return StubLLM()


__all__ = ["GeminiLLM", "LLMError", "OpenAILLM", "ResilientLLM", "StubLLM", "get_llm"]


# ---------------------------------------------------------------------------
# Smoke entry point
# ---------------------------------------------------------------------------

def _smoke() -> None:
    """Tiny smoke that exercises whichever LLM ``get_llm()`` returns.

    Loads ``.env`` from CWD (so ``GEMINI_API_KEY`` is available) and asks
    the configured backend to extract group constraints from a tiny prompt.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:  # noqa: BLE001
        pass

    from .clients.llm_stub import GroupConstraints

    llm = get_llm()
    using_stub = getattr(llm, "using_stub", False)
    print(f"[smoke] using {type(llm).__name__} (using_stub={using_stub})")

    if using_stub and not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("no key, using stub")

    messages = [
        {
            "role": "system",
            "content": (
                "You extract structured group dining constraints from free text. "
                "Return a GroupConstraints JSON object."
            ),
        },
        {
            "role": "user",
            "content": (
                "We want vegetarian, quiet, cheap. Please populate the schema."
            ),
        },
    ]

    async def _run() -> Any:
        return await llm.chat_completion(messages, response_model=GroupConstraints)

    parsed = asyncio.run(_run())
    print("=== parsed GroupConstraints ===")
    print(parsed.model_dump_json(indent=2))


if __name__ == "__main__":
    _smoke()
