from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    graph_name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    trigger: Mapped[str] = mapped_column(nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','failed','interrupted','cancelled')",
            name="agent_runs_status_check",
        ),
        Index("agent_runs_mission_idx", "mission_id", text("started_at DESC")),
        Index("agent_runs_status_idx", "status"),
    )


class AgentRunStep(Base):
    __tablename__ = "agent_run_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("agent_run_steps_run_idx", "agent_run_id", "started_at"),)
