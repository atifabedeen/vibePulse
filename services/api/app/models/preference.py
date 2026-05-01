from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Preference(Base):
    __tablename__ = "preferences"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    budget_max_cents: Mapped[int | None] = mapped_column(nullable=True)
    distance_tolerance_m: Mapped[int | None] = mapped_column(nullable=True)

    cuisines_like: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    cuisines_dislike: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    dietary_restrictions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )

    vibe: Mapped[str | None] = mapped_column(nullable=True)
    noise_tolerance: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    seating_preference: Mapped[str | None] = mapped_column(nullable=True)
    urgency: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hunger_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    raw_comment: Mapped[str | None] = mapped_column(nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
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
