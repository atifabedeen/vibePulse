from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# All three tables (missions, mission_members, mission_invites) live here
# because they share a single domain concept and tend to be edited together.

_MISSION_STATUSES = ("draft", "collecting", "ranking", "voting", "decided", "cancelled")
_MEMBER_ROLES = ("owner", "member")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    creator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)

    location_lat: Mapped[float] = mapped_column(Float, nullable=False)
    location_lng: Mapped[float] = mapped_column(Float, nullable=False)
    search_radius_m: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("3000")
    )
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # NOTE: SQLite can't ALTER a table to add a FK after the fact, and these two
    # columns reference `places(id)` which is created later in the migration.
    # We declare ForeignKey at the ORM level so cascade/relationship logic works
    # in Python; the migration only emits the actual DB-level FK on Postgres.
    winner_place_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("places.id"),
        nullable=True,
    )
    backup_place_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("places.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
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
    role: Mapped[str] = mapped_column(nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','member')",
            name="mission_members_role_check",
        ),
    )


class MissionInvite(Base):
    __tablename__ = "mission_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    mission_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    max_uses: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("10")
    )
    uses: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (Index("mission_invites_mission_idx", "mission_id"),)
