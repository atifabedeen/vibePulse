"""`normalize_places` LangGraph node.

Reads/writes `state.candidates`. Drops candidates that:

  * are missing a corresponding ``places`` row (defensive),
  * have insufficient data for scoring (no rating, no price_level),
  * have a low rating (< 3.0),
  * are hard-rejected by `group_constraints` — i.e. share a cuisine
    with `cuisines_dislike`, or are clearly incompatible with a strict
    dietary restriction (vegetarian/vegan vs. bbq-only/sushi-only/etc.).

Returns the filtered list. Place rows live in the ``places`` table; this
node fetches them by id rather than relying on the old in-memory
registry.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ..db import get_async_session_factory
from ..state import CandidatePlace, GraphState

from app.models import Place  # noqa: E402


# Cuisines that a strict vegetarian member should not be sent to.
_VEG_HARD_REJECT_CUISINES = {"bbq"}

# Cuisines where a vegan member is realistically catered to.
_VEGAN_FRIENDLY_CUISINES = {
    "vegan",
    "thai",
    "ethiopian",
    "indian",
}


def _has_essential_fields(place: Place | None) -> bool:
    if place is None:
        return False
    if place.rating is None or place.price_level is None:
        return False
    return True


def _is_hard_rejected(
    place: Place,
    constraints: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Return (rejected, reason). Reason is informational only."""
    if not constraints:
        return False, ""

    cuisines = {c.lower() for c in (place.cuisines or [])}

    dislikes = {c.lower() for c in (constraints.get("cuisines_dislike") or [])}
    overlap = cuisines & dislikes
    if overlap:
        return True, f"cuisine in dislikes: {sorted(overlap)}"

    dietary = {d.lower() for d in (constraints.get("dietary_restrictions") or [])}
    raw_blob = dict(place.raw_blob or {})

    if "vegan" in dietary:
        # Vegan signal can come from (a) a vegan-friendly cuisine, (b) an
        # explicit vegan_options flag, or (c) a vegetarian_options flag —
        # vegetarian-friendly places generally have at least one vegan dish
        # and are scored lower (not hard-rejected) downstream.
        vegan_ok = bool(cuisines & _VEGAN_FRIENDLY_CUISINES)
        if not vegan_ok and not raw_blob.get("vegan_options") and not raw_blob.get("vegetarian_options"):
            return True, "no vegan-friendly cuisine signal"

    if "vegetarian" in dietary:
        veg_flag = raw_blob.get("vegetarian_options")
        if veg_flag is False:
            return True, "raw_blob marks no vegetarian options"
        if cuisines & _VEG_HARD_REJECT_CUISINES and not veg_flag:
            return True, "bbq cuisine without veg options"

    return False, ""


async def normalize_places(state: GraphState) -> dict[str, Any]:
    """Filter `state.candidates` down to the scoreable, viable set."""
    constraints = state.group_constraints
    if not state.candidates:
        return {"candidates": []}

    place_ids = [str(c.place_id) for c in state.candidates]
    factory = get_async_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(select(Place).where(Place.id.in_(place_ids)))
        ).scalars().all()

    by_id: dict[str, Place] = {row.id: row for row in rows}

    kept: list[CandidatePlace] = []
    for cand in state.candidates:
        place = by_id.get(str(cand.place_id))
        if not _has_essential_fields(place):
            continue
        assert place is not None  # narrowed by the guard above

        if float(place.rating) < 3.0:
            continue

        rejected, _reason = _is_hard_rejected(place, constraints)
        if rejected:
            continue

        kept.append(cand)

    return {"candidates": kept}


__all__ = ["normalize_places"]


if __name__ == "__main__":
    import asyncio

    from ..fixtures.sample_mission import sample_mission_state
    from .search_places import search_places

    async def _smoke() -> None:
        state = sample_mission_state()
        state.group_constraints = {
            "cuisines_like": ["italian", "thai"],
            "cuisines_dislike": ["sushi"],
            "dietary_restrictions": ["vegetarian"],
            "vibe": "casual",
            "noise_tolerance": 2,
            "budget_max_cents": 2000,
        }
        search_update = await search_places(state)
        before = len(search_update["candidates"])
        state.candidates = search_update["candidates"]

        norm_update = await normalize_places(state)
        after = len(norm_update["candidates"])

        print(f"normalize_places: before={before} after={after}")
        for c in norm_update["candidates"]:
            print(f"  kept: {c.name}")

    asyncio.run(_smoke())
