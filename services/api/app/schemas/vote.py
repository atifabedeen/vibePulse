from __future__ import annotations

"""Pydantic schemas for vote endpoints (sec 7.7).

`VotePayload` is what a member sends to express a single up/veto vote.
`VoteTally` is the per-mission aggregation used to render the live
voting screen; `FinalizeOut` returns the chosen winner + backup places
after the owner closes voting.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.place import PlaceOut


class VotePayload(BaseModel):
    """Body for `PUT /votes/me`. weight ∈ {-1, 1}."""

    place_id: str = Field(..., min_length=1, max_length=64)
    weight: Literal[-1, 1] = 1


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mission_id: str
    user_id: str
    place_id: str
    weight: int
    created_at: datetime


class VoteCounts(BaseModel):
    up: int = 0
    veto: int = 0


class VoteTally(BaseModel):
    """`GET /votes/` response — `{place_id: {up: N, veto: M}}`."""

    tally: Dict[str, VoteCounts] = Field(default_factory=dict)


class FinalizeOut(BaseModel):
    """`POST /votes/finalize` response."""

    winner: Optional[PlaceOut] = None
    backup: Optional[PlaceOut] = None
