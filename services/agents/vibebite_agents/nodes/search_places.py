"""`search_places` LangGraph node.

Reads:
  * `state.group_constraints`
  * `state.location`
  * `state.search_radius_m`

Writes:
  * `state.candidates` — list[CandidatePlace] (raw, unscored)

Side effect:
  * Upserts every fetched ``PlaceResult`` into the ``places`` table. The
    DB row's ``id`` (string UUID) becomes the ``CandidatePlace.place_id``
    so downstream nodes can look the place back up by id.

This replaces the C2 in-memory ``state_ext.CANDIDATE_REGISTRY`` hack:
all richer place fields (price_level, rating, cuisines, raw_blob, …) now
live in SQLite and are read back by ``normalize_places`` and
``score_candidates``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from ..clients.places_client import GooglePlacesClient
from ..clients.places_stub import PlaceResult
from ..db import get_async_session_factory
from ..state import CandidatePlace, GraphState

# Import inside the module so import-time failures of `app.database` don't
# break stub-only callers. ``Place`` is referenced unconditionally below.
from app.models import Place  # noqa: E402

# How long a fetched Places row stays fresh before requiring a re-fetch.
_PLACES_TTL = timedelta(days=7)


def _build_query(group_constraints: dict[str, Any] | None) -> str:
    """Compose a text query from the group's cuisine likes."""
    if not group_constraints:
        return "restaurants"
    likes = group_constraints.get("cuisines_like") or []
    if not likes:
        return "restaurants"
    return " ".join(likes) + " restaurants"


async def _upsert_place(session, place: PlaceResult) -> str:
    """Upsert one place row keyed by ``google_place_id``. Return its ``id``."""
    now = datetime.now(timezone.utc)
    expires = now + _PLACES_TTL

    stmt = select(Place).where(Place.google_place_id == place.google_place_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is not None:
        existing.name = place.name
        existing.address = place.address
        existing.lat = place.lat
        existing.lng = place.lng
        existing.price_level = place.price_level
        existing.rating = place.rating
        existing.user_rating_ct = place.user_rating_ct
        existing.cuisines = list(place.cuisines)
        existing.raw_blob = dict(place.raw_blob)
        existing.fetched_at = now
        existing.expires_at = expires
        await session.flush()
        return existing.id

    row = Place(
        google_place_id=place.google_place_id,
        name=place.name,
        address=place.address,
        lat=place.lat,
        lng=place.lng,
        price_level=place.price_level,
        rating=place.rating,
        user_rating_ct=place.user_rating_ct,
        cuisines=list(place.cuisines),
        raw_blob=dict(place.raw_blob),
        fetched_at=now,
        expires_at=expires,
    )
    session.add(row)
    await session.flush()
    return row.id


async def search_places(state: GraphState) -> dict[str, Any]:
    """Run a Places Text Search, persist rows, return CandidatePlaces."""
    client = GooglePlacesClient()
    lat, lng = state.location
    query = _build_query(state.group_constraints)

    results = client.text_search(
        query=query,
        lat=lat,
        lng=lng,
        radius_m=state.search_radius_m,
    )

    factory = get_async_session_factory()
    candidates: list[CandidatePlace] = []
    async with factory() as session:
        try:
            for place in results:
                place_id = await _upsert_place(session, place)
                candidates.append(
                    CandidatePlace(
                        place_id=UUID(place_id),
                        google_place_id=place.google_place_id,
                        name=place.name,
                    )
                )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    return {"candidates": candidates}


__all__ = ["search_places"]


if __name__ == "__main__":
    import asyncio

    from ..fixtures.sample_mission import sample_mission_state

    async def _smoke() -> None:
        state = sample_mission_state()
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
        for c in update["candidates"][:3]:
            print(f"  - {c.name} ({c.google_place_id})")

    asyncio.run(_smoke())
