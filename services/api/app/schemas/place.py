from __future__ import annotations

"""Pydantic schemas for place endpoints (sec 7.5).

`PlaceOut` is the list shape (small enough to render in a card list);
`PlaceDetail` is the same plus the raw Google blob and embedding-derived
extras. The `vibe_embedding` is intentionally **not** exposed — it's an
internal scoring input.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    google_place_id: str
    name: str
    address: Optional[str] = None
    lat: float
    lng: float
    price_level: Optional[int] = None
    rating: Optional[float] = None
    user_rating_ct: Optional[int] = None
    cuisines: List[str] = Field(default_factory=list)
    fetched_at: datetime
    expires_at: datetime


class PlaceDetail(PlaceOut):
    """Adds the raw Google Places blob for the detail view."""

    raw_blob: Dict[str, Any] = Field(default_factory=dict)


class PlaceRefreshOut(BaseModel):
    """Response for `POST /places/refresh` (202)."""

    agent_run_id: str
