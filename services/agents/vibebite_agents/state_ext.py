"""Transient state extension for C2 stub-time scoring.

`GraphState.candidates` is intentionally lean — it carries only the bits
that survive into a finalized ranking (id, name, score, pros, cons).
But `score_candidates` needs the richer Places payload (price_level,
rating, cuisines, raw_blob, lat/lng) to actually compute a score.

We do NOT modify `state.py` (other agents share that contract). Instead
we keep a process-local registry that `search_places` populates and
later nodes read. This is a stub-time hack: in C3 the same data lives
in the `places` Postgres table and is fetched by id, so this module
goes away.

Documented and contained: nothing else in the system depends on this
file other than the C2 nodes that explicitly import it.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtendedCandidate(BaseModel):
    """Richer candidate record used by `score_candidates`.

    Mirrors the subset of `PlaceResult` we actually consume, plus the
    ids that link it back to `state.candidates`.
    """

    place_id: str
    google_place_id: str
    name: str
    lat: float
    lng: float
    price_level: int
    rating: float
    user_rating_ct: int
    cuisines: list[str] = Field(default_factory=list)
    raw_blob: dict = Field(default_factory=dict)


# Module-level registry. Keys are `str(UUID)` so they line up with
# `CandidatePlace.place_id` once that field is stringified.
#
# NOTE: This is a transient in-memory side-channel for the C2 demo;
# will move to the `places` table in C3.
CANDIDATE_REGISTRY: dict[str, ExtendedCandidate] = {}


def reset_registry() -> None:
    """Clear the registry — handy when running smoke tests back-to-back."""
    CANDIDATE_REGISTRY.clear()


def get_extended(place_id: str) -> Optional[ExtendedCandidate]:
    """Look up the richer candidate by place_id (stringified UUID)."""
    return CANDIDATE_REGISTRY.get(place_id)


__all__ = [
    "ExtendedCandidate",
    "CANDIDATE_REGISTRY",
    "reset_registry",
    "get_extended",
]
