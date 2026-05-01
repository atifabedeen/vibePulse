from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    kind: Mapped[str] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    related_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        nullable=True,
    )
    opened_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info','warn','error','critical')",
            name="incidents_severity_check",
        ),
        CheckConstraint(
            "status IN ('open','acknowledged','resolved')",
            name="incidents_status_check",
        ),
        Index("incidents_status_idx", "status", text("opened_at DESC")),
    )
