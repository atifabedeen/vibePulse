"""LangGraph state schema.

Mirrors implementation.md section 8.1 verbatim. `from __future__ import
annotations` defers annotation evaluation so the modern `X | None` union
syntax keeps working on Python 3.9.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MemberPref(BaseModel):
    user_id: UUID
    structured: dict          # snapshot of preferences row
    raw_comment: str | None


class CandidatePlace(BaseModel):
    place_id: UUID
    google_place_id: str
    name: str
    score: float | None = None
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class GraphState(BaseModel):
    # inputs
    mission_id: UUID
    member_prefs: list[MemberPref]
    location: tuple[float, float]
    search_radius_m: int

    # derived
    group_constraints: dict | None = None     # parse_preferences output
    candidates: list[CandidatePlace] = Field(default_factory=list)
    shortlist: list[CandidatePlace] = Field(default_factory=list)

    # voting
    poll_id: UUID | None = None
    votes: dict[str, dict] = Field(default_factory=dict)

    # decision
    winner: CandidatePlace | None = None
    backup: CandidatePlace | None = None

    # control
    needs_human_approval: bool = False
    approval_decision: Literal["approve", "reject"] | None = None

    # observability
    agent_run_id: UUID
