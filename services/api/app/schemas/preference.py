from __future__ import annotations

"""Pydantic schemas for preference endpoints (sec 7.4).

`PreferencePayload` mirrors the columns on the `preferences` table and is
used as the body of `PUT /missions/{id}/preferences/me`. `PreferenceOut`
is the read shape — it adds the path keys (mission_id, user_id) and the
server-managed `updated_at` / `parsed_at` timestamps.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PreferencePayload(BaseModel):
    """Body for `PUT /preferences/me`. All fields optional — caller may
    edit only the bits they care about; missing fields keep their existing
    value on update, default to None / [] on insert."""

    budget_max_cents: Optional[int] = Field(default=None, ge=0)
    distance_tolerance_m: Optional[int] = Field(default=None, ge=0)
    cuisines_like: Optional[List[str]] = None
    cuisines_dislike: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None
    vibe: Optional[str] = Field(default=None, max_length=255)
    noise_tolerance: Optional[int] = Field(default=None, ge=0, le=5)
    seating_preference: Optional[str] = Field(default=None, max_length=32)
    urgency: Optional[int] = Field(default=None, ge=0, le=5)
    hunger_level: Optional[int] = Field(default=None, ge=0, le=5)
    raw_comment: Optional[str] = Field(default=None, max_length=4000)


class PreferenceParseIn(BaseModel):
    """Body for `POST /preferences/me/parse`."""

    raw_comment: str = Field(..., min_length=1, max_length=4000)


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mission_id: str
    user_id: str
    budget_max_cents: Optional[int] = None
    distance_tolerance_m: Optional[int] = None
    cuisines_like: List[str] = Field(default_factory=list)
    cuisines_dislike: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    vibe: Optional[str] = None
    noise_tolerance: Optional[int] = None
    seating_preference: Optional[str] = None
    urgency: Optional[int] = None
    hunger_level: Optional[int] = None
    raw_comment: Optional[str] = None
    parsed_at: Optional[datetime] = None
    updated_at: datetime
