"""Stub LLM client.

This is NOT a real LLM. It is a deterministic keyword-spotter that returns
populated Pydantic instances so the rest of the graph can run without an
OpenAI key. Behavior:

  * `stub_chat_completion(messages, response_model)` inspects the user
    message text for a small set of keywords and produces a plausible
    structured output.
  * Two `response_model` shapes are supported by name: `GroupConstraints`
    (the `parse_preferences` output) and `CandidateExplanation` (the
    `explain_candidates` per-place output). Both ship in this file as
    BaseModels for now; the graph will redefine them at C2 alongside the
    real prompt schemas.

Keyword map (case-insensitive substring match anywhere in `messages`):

  * "vegetarian"    -> dietary_restrictions includes "vegetarian"
  * "vegan"         -> dietary_restrictions includes "vegan"
  * "cheap"/"budget"-> budget_max_cents = 1500 (i.e. ~$15)
  * "fancy"         -> budget_max_cents = 8000 (i.e. ~$80)
  * "loud"          -> noise_tolerance = 5, vibe = "lively"
  * "quiet"         -> noise_tolerance = 1, vibe = "quiet"
  * "casual"        -> vibe = "casual" (does not override "lively"/"quiet")
  * "sushi"         -> cuisines_dislike includes "sushi"
                      (interpreted as "someone refuses sushi")

For `CandidateExplanation` the stub picks generic pros/cons biased by the
detected keywords (e.g. veg keywords + a place described as veg-friendly
yields a vegetarian-options pro).

Real LLM calls land in C2/C3 via `models.py`.
"""

from __future__ import annotations

from typing import Any, Iterable, Type, TypeVar, Union

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class GroupConstraints(BaseModel):
    """Structured output for `parse_preferences`.

    Mirrors the columns we eventually persist as a per-mission constraint
    profile. C2 may rename or restructure this; for now it lets the stub
    return something the score node can read.
    """

    budget_max_cents: int | None = None
    cuisines_like: list[str] = Field(default_factory=list)
    cuisines_dislike: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    vibe: str | None = None
    noise_tolerance: int | None = None  # 0 (silent) - 5 (loud)
    seating_preference: str | None = None
    summary: str = ""


class CandidateExplanation(BaseModel):
    """Structured output for `explain_candidates` (one per place)."""

    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


# Internal type alias for a chat-style messages list. We accept both the
# OpenAI shape (list of {"role","content"} dicts) and a plain string so
# tests can be terse.
MessagesType = Union[str, Iterable[dict[str, Any]]]


def _flatten_messages(messages: MessagesType) -> str:
    """Concatenate message contents into a single lowercase string."""
    if isinstance(messages, str):
        return messages.lower()
    parts: list[str] = []
    for m in messages:
        content = m.get("content", "") if isinstance(m, dict) else ""
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for chunk in content:
                if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                    parts.append(chunk["text"])
    return " ".join(parts).lower()


def _stub_group_constraints(text: str) -> GroupConstraints:
    out = GroupConstraints(summary="stub-parsed group constraints")

    dietary: list[str] = []
    if "vegan" in text:
        dietary.append("vegan")
    if "vegetarian" in text and "vegetarian" not in dietary:
        dietary.append("vegetarian")
    out.dietary_restrictions = dietary

    if "cheap" in text or "budget" in text:
        out.budget_max_cents = 1500
    elif "fancy" in text:
        out.budget_max_cents = 8000

    if "loud" in text:
        out.noise_tolerance = 5
        out.vibe = "lively"
    elif "quiet" in text:
        out.noise_tolerance = 1
        out.vibe = "quiet"
    elif "casual" in text:
        out.vibe = "casual"

    if "sushi" in text:
        out.cuisines_dislike.append("sushi")

    return out


def _stub_candidate_explanation(text: str) -> CandidateExplanation:
    pros: list[str] = []
    cons: list[str] = []

    if "vegetarian" in text or "vegan" in text:
        pros.append("Has clearly labeled vegetarian options.")
    if "cheap" in text or "budget" in text:
        pros.append("Price level fits a tight budget.")
    if "quiet" in text:
        pros.append("Quiet enough for conversation.")
        cons.append("May feel sleepy if the group wants energy.")
    if "loud" in text:
        pros.append("Lively atmosphere good for a celebration.")
        cons.append("Hard to hear across a 5-person table.")
    if "casual" in text:
        pros.append("Dress code is casual, no fuss.")
    if "sushi" in text:
        cons.append("Menu leans heavily on sushi — not for everyone.")

    if not pros:
        pros.append("Solid all-around fit for the group.")
    if not cons:
        cons.append("No standout drawbacks based on available info.")

    return CandidateExplanation(pros=pros, cons=cons)


def stub_chat_completion(messages: MessagesType, response_model: Type[T]) -> T:
    """Return a populated `response_model` instance via keyword spotting.

    This function exists so node code at C2 can write::

        result = llm.chat_completion(messages, response_model=GroupConstraints)

    and the call works identically against the stub or the real client. See
    the module docstring for the keyword-to-field mapping.
    """
    text = _flatten_messages(messages)

    # Dispatch by class name so we don't have to import anything from C2.
    name = response_model.__name__
    if name == "GroupConstraints":
        return response_model.model_validate(_stub_group_constraints(text).model_dump())
    if name == "CandidateExplanation":
        return response_model.model_validate(_stub_candidate_explanation(text).model_dump())

    # Fallback: try to construct an empty instance. If the model has no
    # required fields this works; otherwise we surface a clear error so the
    # caller knows to extend the stub.
    try:
        return response_model()
    except Exception as exc:  # noqa: BLE001 - intentional broad catch on stub
        raise NotImplementedError(
            f"llm_stub does not know how to populate {name!r}. Extend "
            "stub_chat_completion or pass a model with no required fields."
        ) from exc


__all__ = [
    "CandidateExplanation",
    "GroupConstraints",
    "stub_chat_completion",
]
