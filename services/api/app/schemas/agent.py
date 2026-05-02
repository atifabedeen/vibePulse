from __future__ import annotations

"""Pydantic schemas for the agents router (sec 7.8).

`AgentRunOut`     — list shape: one row from `agent_runs`.
`AgentRunStepOut` — embedded step row used in the detail view.
`AgentRunDetail`  — `AgentRunOut` + `steps[]`.
`AgentRejectIn`   — body for `POST /runs/{id}/reject`.
`AgentResumeOut`  — small ack returned by approve/reject.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mission_id: str
    graph_name: str
    status: str
    trigger: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None


class AgentRunStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    node_name: str
    status: str
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class AgentRunDetail(AgentRunOut):
    steps: List[AgentRunStepOut] = Field(default_factory=list)


class AgentRejectIn(BaseModel):
    """Body for `POST /runs/{id}/reject`."""

    reason: str = Field(..., min_length=1, max_length=2000)
    overrides: Optional[Dict[str, Any]] = None


class AgentResumeOut(BaseModel):
    """Ack returned by approve/reject."""

    agent_run_id: str
    status: str
