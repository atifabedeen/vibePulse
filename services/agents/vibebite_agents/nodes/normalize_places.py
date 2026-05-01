"""`normalize_places` LangGraph node.

Reads/writes `state.candidates`. Drops candidates that:

  * are missing the registry-side richer record (search_places didn't
    populate it — defensive),
  * have insufficient data for scoring (no rating, no price_level),
  * have a low rating (< 3.0),
  * are hard-rejected by `group_constraints` — i.e. share a cuisine
    with `cuisines_dislike`, or are clearly incompatible with a strict
    dietary restriction (vegetarian/vegan vs. bbq-only/sushi-only/etc.).

Returns the filtered list. The registry is also pruned of dropped
candidates so the downstream score node doesn't carry dead weight.
"""

from __future__ import annotations

from typing import Any

from ..state import CandidatePlace, GraphState
from ..state_ext import CANDIDATE_REGISTRY, ExtendedCandidate


# Cuisines that a strict vegetarian member should not be sent to.
# (Conservative — these are establishments where the menu is overwhelmingly
# meat-forward and there's no reliable veg option signaled.)
_VEG_HARD_REJECT_CUISINES = {"bbq"}

# Cuisines where a vegan member is realistically catered to. The fixture
# and real Places data don't always tag `vegan_options`, so we use cuisine
# heuristics — see implementation.md sec 8.2 score row.
_VEGAN_FRIENDLY_CUISINES = {
    "vegan",
    "thai",
    "ethiopian",
    "indian",
}


def _has_essential_fields(ext: ExtendedCandidate | None) -> bool:
    if ext is None:
        return False
    if ext.rating is None or ext.price_level is None:
        return False
    return True


def _is_hard_rejected(
    ext: ExtendedCandidate,
    constraints: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Return (rejected, reason). Reason is informational only."""
    if not constraints:
        return False, ""

    cuisines = {c.lower() for c in ext.cuisines}

    dislikes = {c.lower() for c in (constraints.get("cuisines_dislike") or [])}
    overlap = cuisines & dislikes
    if overlap:
        return True, f"cuisine in dislikes: {sorted(overlap)}"

    dietary = {d.lower() for d in (constraints.get("dietary_restrictions") or [])}

    if "vegan" in dietary:
        # The candidate must be in a vegan-friendly cuisine bucket OR
        # explicitly flag vegan options in the raw blob.
        vegan_ok = bool(cuisines & _VEGAN_FRIENDLY_CUISINES)
        if not vegan_ok and not ext.raw_blob.get("vegan_options"):
            return True, "no vegan-friendly cuisine signal"

    if "vegetarian" in dietary:
        # If we have an explicit vegetarian_options=False from the raw blob,
        # that's a hard no. Otherwise reject only on bbq-only joints.
        veg_flag = ext.raw_blob.get("vegetarian_options")
        if veg_flag is False:
            return True, "raw_blob marks no vegetarian options"
        if cuisines & _VEG_HARD_REJECT_CUISINES and not veg_flag:
            return True, "bbq cuisine without veg options"

    return False, ""


async def normalize_places(state: GraphState) -> dict[str, Any]:
    """Filter `state.candidates` down to the scoreable, viable set."""
    constraints = state.group_constraints
    kept: list[CandidatePlace] = []
    dropped_ids: list[str] = []

    for cand in state.candidates:
        key = str(cand.place_id)
        ext = CANDIDATE_REGISTRY.get(key)

        if not _has_essential_fields(ext):
            dropped_ids.append(key)
            continue

        # mypy/runtime: ext is non-None past the guard.
        assert ext is not None

        if ext.rating < 3.0:
            dropped_ids.append(key)
            continue

        rejected, _reason = _is_hard_rejected(ext, constraints)
        if rejected:
            dropped_ids.append(key)
            continue

        kept.append(cand)

    # Prune the registry so downstream nodes see a clean view.
    for key in dropped_ids:
        CANDIDATE_REGISTRY.pop(key, None)

    return {"candidates": kept}


__all__ = ["normalize_places"]


if __name__ == "__main__":
    import asyncio

    from ..fixtures.sample_mission import sample_mission_state
    from ..state_ext import reset_registry
    from .search_places import search_places

    async def _smoke() -> None:
        reset_registry()
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
