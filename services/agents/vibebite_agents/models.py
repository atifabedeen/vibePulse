"""LLM client wrapper.

A thin shim that node code can import without caring whether the real
OpenAI client or the local stub is in use.

Selection rules:

  * If `VIBEBITE_USE_STUBS=1` is set, the stub LLM is always used.
  * Else if `OPENAI_API_KEY` is unset, the stub LLM is used.
  * Otherwise the real client is used (NotImplemented at C1-C; lands in C2).

Public surface (mirrors what `parse_preferences` and `explain_candidates`
will call):

    llm = get_llm()
    result = llm.chat_completion(messages, response_model=GroupConstraints)

`messages` follows the OpenAI chat shape: `[{"role": "user", "content": "..."}]`.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from .clients.llm_stub import stub_chat_completion

T = TypeVar("T", bound=BaseModel)
MessagesType = Union[str, Iterable[dict[str, Any]]]


class StubLLM:
    """Drop-in stand-in for the real OpenAI client at C1-C."""

    using_stub = True

    def chat_completion(self, messages: MessagesType, response_model: Type[T]) -> T:
        return stub_chat_completion(messages, response_model)


class OpenAILLM:
    """Real OpenAI-backed LLM. Implementation lands in C2.

    Kept as a clearly-typed placeholder so downstream code can reference the
    eventual class name without a future rename breaking imports.
    """

    using_stub = False

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def chat_completion(self, messages: MessagesType, response_model: Type[T]) -> T:
        raise NotImplementedError(
            "Real OpenAI client lands in C2. Set VIBEBITE_USE_STUBS=1 or unset "
            "OPENAI_API_KEY to use the StubLLM in the meantime."
        )


def get_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    force_stub: Optional[bool] = None,
) -> Union[StubLLM, OpenAILLM]:
    """Return the configured LLM client.

    The defaults read `OPENAI_API_KEY`, `OPENAI_MODEL`, and
    `VIBEBITE_USE_STUBS` from the environment so node code can be one-line:

        llm = get_llm()
    """
    if force_stub is None:
        force_stub = os.environ.get("VIBEBITE_USE_STUBS") == "1"
    resolved_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
    if force_stub or not resolved_key:
        return StubLLM()
    resolved_model = model if model is not None else os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return OpenAILLM(api_key=resolved_key, model=resolved_model)


__all__ = ["OpenAILLM", "StubLLM", "get_llm"]
