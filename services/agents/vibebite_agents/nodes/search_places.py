"""`search_places` LangGraph node.

Reads:
  * `state.group_constraints`
  * `state.location`
  * `state.search_radius_m`

Writes:
  * `state.candidates` — list[CandidatePlace] (raw, unscored)

Side effect:
  * Populates `state_ext.CANDIDATE_REGISTRY` so that `normalize_places`
    and `score_candidates` can read the richer `PlaceResult` fields
    that don't fit on `CandidatePlace`. See `state_ext.py` for why.

In C3 this node will write upserts into the `places` table and emit
`places_api_calls_total`; for C2 the side-channel registry is enough.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from ..clients.places_client import GooglePlacesClient
from ..clients.places_stub import PlaceResult
from ..state import CandidatePlace, GraphState
from ..state_ext import CANDIDATE_REGISTRY, ExtendedCandidate


def _build_query(group_constraints: dict[str, Any] | None) -> str:
    """Compose a text query from the group's cuisine likes.

    Falls back to a generic 'restaurants' query when there's nothing
    to bias on. Real Places Text Search responds noticeably better to
    a cuisine-flavoured query than to an empty one.
    """
    if not group_constraints:
        return "restaurants"
    likes = group_constraints.get("cuisines_like") or []
    if not likes:
        return "restaurants"
    # Join with spaces — Text Search treats this as a soft OR.
    return " ".join(likes) + " restaurants"


def _to_candidate(place: PlaceResult) -> CandidatePlace:
    """Convert a `PlaceResult` to the lean `CandidatePlace` carried in state.

    `score`, `pros`, `cons` are deliberately left at their defaults;
    `score_candidates` fills them.
    """
    return CandidatePlace(
        place_id=UUID(place.id),
        google_place_id=place.google_place_id,
        name=place.name,
    )


def _register_extended(place: PlaceResult) -> None:
    """Stash the richer fields so downstream nodes can score them."""
    CANDIDATE_REGISTRY[place.id] = ExtendedCandidate(
        place_id=place.id,
        google_place_id=place.google_place_id,
        name=place.name,
        lat=place.lat,
        lng=place.lng,
        price_level=place.price_level,
        rating=place.rating,
        user_rating_ct=place.user_rating_ct,
        cuisines=list(place.cuisines),
        raw_blob=dict(place.raw_blob),
    )


async def search_places(state: GraphState) -> dict[str, Any]:
    """Run a Places Text Search and return the resulting candidates."""
    client = GooglePlacesClient()
    lat, lng = state.location
    query = _build_query(state.group_constraints)

    results = client.text_search(
        query=query,
        lat=lat,
        lng=lng,
        radius_m=state.search_radius_m,
    )

    candidates: list[CandidatePlace] = []
    for place in results:
        _register_extended(place)
        candidates.append(_to_candidate(place))

    return {"candidates": candidates}


__all__ = ["search_places"]


if __name__ == "__main__":
    import asyncio

    from ..fixtures.sample_mission import sample_mission_state
    from ..state_ext import reset_registry

    async def _smoke() -> None:
        reset_registry()
        state = sample_mission_state()
        # Provide a minimal group_constraints so the query is non-trivial.
        state.group_constraints = {
            "cuisines_like": ["italian", "thai"],
            "cuisines_dislike": [],
            "dietary_restrictions": ["vegetarian"],
            "vibe": "casual",
            "noise_tolerance": 2,
            "budget_max_cents": 2000,
        }
        update = await search_places(state)
        print(f"search_places fetched {len(update['candidates'])} candidates")
        print(f"registry size: {len(CANDIDATE_REGISTRY)}")
        for c in update["candidates"][:3]:
            print(f"  - {c.name} ({c.google_place_id})")

    asyncio.run(_smoke())
