from __future__ import annotations

"""Pydantic schemas for ranking endpoints (sec 7.6).

A ranking row pairs a place with its score + reasons under a specific
agent_run_id. The list endpoints group by agent_run_id so the client can
render "this is the latest ranking from run X" semantics.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class RankingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mission_id: str
    place_id: str
    agent_run_id: str
    rank: int
    score: float
    reasons: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RankingBatch(BaseModel):
    """Returned by `GET /rankings/latest` and `GET /rankings/runs/{run_id}`."""

    agent_run_id: str | None = None
    items: List[RankingItem] = Field(default_factory=list)
