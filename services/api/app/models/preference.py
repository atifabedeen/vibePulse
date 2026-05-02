from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Preference(Base):
    __tablename__ = "preferences"

    mission_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("missions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    budget_max_cents: Mapped[Optional[int]] = mapped_column(nullable=True)
    distance_tolerance_m: Mapped[Optional[int]] = mapped_column(nullable=True)

    # text[] in the original Postgres schema -> JSON list-of-strings here so
    # the column travels cleanly to SQLite.
    cuisines_like: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    cuisines_dislike: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    dietary_restrictions: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    vibe: Mapped[Optional[str]] = mapped_column(nullable=True)
    noise_tolerance: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    seating_preference: Mapped[Optional[str]] = mapped_column(nullable=True)
    urgency: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    hunger_level: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    raw_comment: Mapped[Optional[str]] = mapped_column(nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "noise_tolerance BETWEEN 0 AND 5",
            name="preferences_noise_tolerance_check",
        ),
        CheckConstraint(
            "urgency BETWEEN 0 AND 5",
            name="preferences_urgency_check",
        ),
        CheckConstraint(
            "hunger_level BETWEEN 0 AND 5",
            name="preferences_hunger_level_check",
        ),
    )
