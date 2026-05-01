from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# All three tables (missions, mission_members, mission_invites) live here
# because they share a single domain concept and tend to be edited together.

_MISSION_STATUSES = ("draft", "collecting", "ranking", "voting", "decided", "cancelled")
_MEMBER_ROLES = ("owner", "member")


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)

    location_lat: Mapped[float] = mapped_column(Float, nullable=False)
    location_lng: Mapped[float] = mapped_column(Float, nullable=False)
    search_radius_m: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("3000")
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(nullable=True)

    winner_place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id"),
        nullable=True,
    )
    backup_place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','collecting','ranking','voting','decided','cancelled')",
            name="missions_status_check",
        ),
        Index("missions_creator_idx", "creator_id"),
        Index("missions_status_idx", "status"),
    )


class MissionMember(Base):
    __tablename__ = "mission_members"

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
    role: Mapped[str] = mapped_column(nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','member')",
            name="mission_members_role_check",
        ),
    )


class MissionInvite(Base):
    __tablename__ = "mission_invites"

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
    token: Mapped[str] = mapped_column(unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    max_uses: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("10")
    )
    uses: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )

    __table_args__ = (Index("mission_invites_mission_idx", "mission_id"),)
