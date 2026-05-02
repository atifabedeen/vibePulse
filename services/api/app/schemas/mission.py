from __future__ import annotations

"""Pydantic schemas for the missions API surface (spec sec 7.3).

Kept intentionally narrow: only fields the spec exposes on the wire end up
here. ORM models in `app.models.mission` carry the storage contract; these
schemas carry the HTTP contract. Don't try to unify them — they evolve at
different rates and have different audiences.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LatLng(BaseModel):
    """Plain {lat, lng} object — used in MissionCreate and MissionOut."""

    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)


class MissionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    location: LatLng
    # Spec default 3000m; clamp to a sane range so we don't blow up downstream
    # Google Places calls.
    search_radius_m: int = Field(default=3000, ge=100, le=50_000)
    scheduled_for: Optional[datetime] = None


class MissionUpdate(BaseModel):
    """All fields optional — PATCH semantics. Owner-only on the route."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    location: Optional[LatLng] = None
    search_radius_m: Optional[int] = Field(default=None, ge=100, le=50_000)
    scheduled_for: Optional[datetime] = None
    # Status transitions are validated on the service side against the
    # allowed enum (see _MISSION_STATUSES in models.mission).
    status: Optional[str] = None


class MissionOut(BaseModel):
    """Compact mission summary returned by POST/GET list/PATCH."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: str
    title: str
    description: Optional[str]
    status: str
    location: LatLng
    search_radius_m: int
    scheduled_for: Optional[datetime]
    winner_place_id: Optional[str] = None
    backup_place_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MissionMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    role: str
    joined_at: datetime


class MissionDetailOut(MissionOut):
    """Full mission view for `GET /missions/{id}` — includes members."""

    members: List[MissionMemberOut] = Field(default_factory=list)


class MissionListOut(BaseModel):
    items: List[MissionOut]
    next_cursor: Optional[str] = None


class InviteCreate(BaseModel):
    # Spec uses these names; both have safe defaults so callers can POST {}.
    expires_in_hours: int = Field(default=24 * 7, ge=1, le=24 * 30)
    max_uses: int = Field(default=10, ge=1, le=1000)


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mission_id: str
    token: str
    expires_at: datetime
    max_uses: int
    uses: int
    created_at: datetime


class RedeemIn(BaseModel):
    token: str = Field(..., min_length=1, max_length=128)


class ReplanIn(BaseModel):
    # `reason` per spec sec 7.3; free-form, length-capped.
    reason: Optional[str] = Field(default=None, max_length=2000)
    # C5-D extension: optional structured overrides forwarded to the
    # graph as ``_replan_overrides`` (e.g. {"budget_max_cents": 1500}).
    overrides: Optional[Dict[str, Any]] = None


class ReplanOut(BaseModel):
    agent_run_id: str
