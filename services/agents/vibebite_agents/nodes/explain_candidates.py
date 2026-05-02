"""`explain_candidates` LangGraph node.

Reads:
  * ``state.candidates``         — already scored & sorted descending
  * ``state.group_constraints``  — emitted by ``parse_preferences``
  * ``places`` table             — for richer per-place context (cuisine,
                                   price, rating, vibe blob)

Writes:
  * ``state.candidates`` — the same list, but the top-5 entries get
    LLM-generated pros/cons replacing the deterministic ones.
  * ``state.shortlist``  — the same top-5 (matches spec sec 8.1).

Per the spec, this is one LLM call per top-5 candidate, run in
parallel with ``asyncio.gather`` so total latency stays bounded.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import select

from ..clients.llm_stub import CandidateExplanation
from ..db import get_async_session_factory
from ..models import LLMError, get_llm
from ..state import CandidatePlace, GraphState

from app.models import Place  # noqa: E402

# How many top candidates we ask the LLM to explain.
_TOP_N = 5


def _build_messages(
    place: Place,
    cand: CandidatePlace,
    constraints: dict[str, Any],
) -> list[dict[str, Any]]:
    """Render a per-place prompt the LLM can answer with pros/cons."""
    blob = dict(place.raw_blob or {})
    place_view = {
        "name": place.name,
        "cuisines": list(place.cuisines or []),
        "price_level": place.price_level,
        "rating": float(place.rating) if place.rating is not None else None,
        "vibe": blob.get("vibe"),
        "noise": blob.get("noise"),
        "vegetarian_options": blob.get("vegetarian_options"),
        "vegan_options": blob.get("vegan_options"),
        "summary": blob.get("summary"),
    }
    constraint_view = {
        "budget_max_cents": constraints.get("budget_max_cents"),
        "cuisines_like": constraints.get("cuisines_like") or [],
        "cuisines_dislike": constraints.get("cuisines_dislike") or [],
        "dietary_restrictions": constraints.get("dietary_restrictions") or [],
        "vibe": constraints.get("vibe"),
        "noise_tolerance": constraints.get("noise_tolerance"),
        "seating_preference": constraints.get("seating_preference"),
    }

    system = (
        "You are a group dinner advisor. Given a group's constraints and a "
        "candidate restaurant, return a CandidateExplanation JSON object with "
        "2-3 specific pros and 1-2 specific cons. Be concrete: cite cuisine, "
        "price, vibe, dietary fit, or noise — do NOT say 'good for groups' "
        "without a reason. Return exactly the schema fields."
    )
    user = (
        "Group constraints:\n"
        f"{json.dumps(constraint_view, indent=2)}\n\n"
        "Restaurant:\n"
        f"{json.dumps(place_view, indent=2)}\n\n"
        "Return: {\"pros\": [..2-3..], \"cons\": [..1-2..]}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def _explain_one(
    place: Place,
    cand: CandidatePlace,
    constraints: dict[str, Any],
) -> CandidatePlace:
    """LLM-explain a single candidate; on failure fall back to existing pros/cons."""
    llm = get_llm()
    messages = _build_messages(place, cand, constraints)
    try:
        result = await llm.chat_completion(
            messages, response_model=CandidateExplanation
        )
        pros = list(result.pros) or list(cand.pros)
        cons = list(result.cons) or list(cand.cons)
    except (LLMError, Exception):  # noqa: BLE001 - keep the demo runnable
        pros = list(cand.pros)
        cons = list(cand.cons)
    return cand.model_copy(update={"pros": pros, "cons": cons})


async def explain_candidates(state: GraphState) -> dict[str, Any]:
    """Replace deterministic pros/cons with LLM-generated ones for top-5."""
    if not state.candidates:
        return {"candidates": [], "shortlist": []}

    constraints = state.group_constraints or {}
    top = state.candidates[:_TOP_N]
    rest = state.candidates[_TOP_N:]

    # Fetch the corresponding Place rows in one query.
    factory = get_async_session_factory()
    place_ids = [str(c.place_id) for c in top]
    async with factory() as session:
        rows = (
            await session.execute(select(Place).where(Place.id.in_(place_ids)))
        ).scalars().all()
    by_id: dict[str, Place] = {row.id: row for row in rows}

    coros = []
    for cand in top:
        place = by_id.get(str(cand.place_id))
        if place is None:
            # Defensive: if the place vanished, just keep the existing entry.
            async def _passthrough(c: CandidatePlace = cand) -> CandidatePlace:
                return c
            coros.append(_passthrough())
        else:
            coros.append(_explain_one(place, cand, constraints))

    enriched_top = await asyncio.gather(*coros)
    new_candidates = list(enriched_top) + list(rest)
    shortlist = list(enriched_top)
    return {"candidates": new_candidates, "shortlist": shortlist}


__all__ = ["explain_candidates"]


if __name__ == "__main__":
    from ..fixtures.sample_mission import sample_mission_state
    from .normalize_places import normalize_places
    from .parse_preferences import parse_preferences
    from .score_candidates import score_candidates
    from .search_places import search_places

    async def _smoke() -> None:
        state = sample_mission_state()
        upd = await parse_preferences(state)
        state.group_constraints = upd["group_constraints"]
        upd = await search_places(state)
        state.candidates = upd["candidates"]
        upd = await normalize_places(state)
        state.candidates = upd["candidates"]
        upd = await score_candidates(state)
        state.candidates = upd["candidates"]
        upd = await explain_candidates(state)
        for c in upd["shortlist"]:
            print(f"  {c.score:6.2f}  {c.name}")
            for p in c.pros:
                print(f"          + {p}")
            for ct in c.cons:
                print(f"          - {ct}")

    asyncio.run(_smoke())
