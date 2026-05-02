"""parse_preferences node.

Implements section 8.2 of implementation.md: read each member's
preferences (a `structured` snapshot dict plus an optional `raw_comment`
free-text), turn the comment into structured fields via the LLM, and
merge the per-member views into a single shared **group constraint
profile** that downstream nodes (search_places, score_candidates,
explain_candidates) can rely on.

Merge rules
-----------
The merge is intentionally conservative — when in doubt, the rule
favors the member with the tightest preference, because a group
recommendation should not violate anyone's hard constraint.

* ``budget_max_cents``       -- minimum non-null value across members
                                (the member with the tightest budget
                                caps the group's spend).
* ``dietary_restrictions``   -- union (everyone's restrictions stack).
* ``cuisines_like``          -- union (anyone may suggest a liked
                                cuisine).
* ``cuisines_dislike``       -- union (vetoes are sticky: one veto =
                                group veto).
* ``noise_tolerance``        -- minimum non-null value (most
                                noise-averse member wins; loud
                                restaurants exclude them).
* ``vibe``                   -- most common non-null value across
                                members; ties broken alphabetically so
                                output is deterministic.
* ``distance_tolerance_m``   -- minimum non-null value (group cannot
                                travel further than the least
                                travel-tolerant member).
* ``seating_preference``     -- most common non-null value, alphabetic
                                tie-break.

Per-member structured input takes precedence over LLM-parsed values
from the free-text comment when both exist (explicit user input beats
inference).

Per-member parsed results are also stashed under
``group_constraints["per_member"]`` keyed by ``str(user_id)`` so
explanation nodes can cite which member each constraint came from.

Side effect (real DB)
---------------------
In production this node would also stamp ``preferences.parsed_at``
for each member row. For C2 stub work we skip that — the demo
runner has no DB connection and other agents (C2-B/C) will plumb
the persistence layer.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any, Iterable, Optional

from ..clients.llm_stub import GroupConstraints
from ..models import get_llm
from ..prompts import GROUP_FOOD_RECOMMENDATION
from ..state import GraphState, MemberPref


def _coerce_list(value: Any) -> list[str]:
    """Normalize a maybe-list-of-strings into a clean list of strings."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    return []


def _union_preserving_order(*sources: Iterable[str]) -> list[str]:
    """Union of string iterables, preserving first-seen order."""
    seen: dict[str, None] = {}
    for src in sources:
        for item in src:
            if item not in seen:
                seen[item] = None
    return list(seen.keys())


def _min_non_null(values: Iterable[Optional[int]]) -> Optional[int]:
    """Smallest non-null int, or None if every value is None."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return min(filtered)


def _mode_alpha_tiebreak(values: Iterable[Optional[str]]) -> Optional[str]:
    """Most common non-null string; ties resolve alphabetically."""
    filtered = [v for v in values if v]
    if not filtered:
        return None
    counts = Counter(filtered)
    top_count = max(counts.values())
    candidates = sorted(k for k, c in counts.items() if c == top_count)
    return candidates[0]


def _build_messages(member: MemberPref) -> list[dict[str, Any]]:
    """Render the GROUP_FOOD_RECOMMENDATION prompt for a single member.

    The real C2 prompt will batch all members; for the stub LLM we send
    one call per member because the stub keyword-spots a single comment
    at a time and we want per-member parsed output for the
    ``per_member`` section.
    """
    raw = member.raw_comment or ""
    rendered = GROUP_FOOD_RECOMMENDATION.format(
        member_prefs=raw,
        location="(unspecified — set on GraphState)",
    )
    return [
        {"role": "system", "content": "Extract a GroupConstraints JSON object."},
        {"role": "user", "content": rendered},
    ]


def _merge_member_view(
    structured: dict[str, Any],
    parsed: GroupConstraints,
) -> dict[str, Any]:
    """Merge one member's structured prefs over the LLM-parsed comment.

    Structured (explicit) input wins on scalar fields; list fields
    (cuisines, dietary restrictions) are unioned so a comment that adds
    "vegetarian" to a member whose structured row was empty still
    contributes the restriction.
    """
    parsed_dict = parsed.model_dump()

    merged: dict[str, Any] = {}

    # Scalar fields: structured value wins when present (not None).
    for key in (
        "budget_max_cents",
        "vibe",
        "noise_tolerance",
        "seating_preference",
        "distance_tolerance_m",
    ):
        s_val = structured.get(key)
        p_val = parsed_dict.get(key)
        merged[key] = s_val if s_val is not None else p_val

    # List fields: union, structured first so its order leads.
    for key in ("cuisines_like", "cuisines_dislike", "dietary_restrictions"):
        merged[key] = _union_preserving_order(
            _coerce_list(structured.get(key)),
            _coerce_list(parsed_dict.get(key)),
        )

    # Carry the LLM summary verbatim (structured rows have no summary).
    merged["summary"] = parsed_dict.get("summary", "")
    return merged


async def parse_preferences(state: GraphState) -> dict[str, Any]:
    """Turn `state.member_prefs` into a merged group constraint profile.

    Returns the LangGraph partial-state update::

        {"group_constraints": {...}}

    See module docstring for merge semantics.
    """
    llm = get_llm()

    per_member: dict[str, dict[str, Any]] = {}
    member_views: list[dict[str, Any]] = []

    for member in state.member_prefs:
        if member.raw_comment:
            messages = _build_messages(member)
            parsed = await llm.chat_completion(messages, response_model=GroupConstraints)
        else:
            parsed = GroupConstraints(summary="no raw_comment provided")

        merged = _merge_member_view(member.structured or {}, parsed)
        per_member[str(member.user_id)] = merged
        member_views.append(merged)

    # Cross-member merge.
    group: dict[str, Any] = {
        "budget_max_cents": _min_non_null(v.get("budget_max_cents") for v in member_views),
        "dietary_restrictions": _union_preserving_order(
            *(v.get("dietary_restrictions", []) for v in member_views)
        ),
        "cuisines_like": _union_preserving_order(
            *(v.get("cuisines_like", []) for v in member_views)
        ),
        "cuisines_dislike": _union_preserving_order(
            *(v.get("cuisines_dislike", []) for v in member_views)
        ),
        "noise_tolerance": _min_non_null(v.get("noise_tolerance") for v in member_views),
        "vibe": _mode_alpha_tiebreak(v.get("vibe") for v in member_views),
        "distance_tolerance_m": _min_non_null(
            v.get("distance_tolerance_m") for v in member_views
        ),
        "seating_preference": _mode_alpha_tiebreak(
            v.get("seating_preference") for v in member_views
        ),
        "per_member": per_member,
    }

    # NOTE (C2): when the real DB layer lands, also UPDATE
    # preferences.parsed_at = now() for each member.user_id here.

    return {"group_constraints": group}


def _smoke() -> None:
    """Sync entrypoint that runs the node against the sample fixture.

    Use::

        python -m vibebite_agents.nodes.parse_preferences

    to sanity-check the merge rules without spinning up LangGraph.
    """
    from ..fixtures.sample_mission import sample_mission_state

    state = sample_mission_state()
    result = asyncio.run(parse_preferences(state))
    constraints = result["group_constraints"]

    print("=== merged group_constraints ===")
    for key in (
        "budget_max_cents",
        "dietary_restrictions",
        "cuisines_like",
        "cuisines_dislike",
        "noise_tolerance",
        "vibe",
        "distance_tolerance_m",
        "seating_preference",
    ):
        print(f"  {key}: {constraints.get(key)!r}")

    print("=== per_member (user_id -> merged view) ===")
    for user_id, view in constraints["per_member"].items():
        print(f"  {user_id}:")
        for k, v in view.items():
            print(f"      {k}: {v!r}")


if __name__ == "__main__":
    _smoke()
