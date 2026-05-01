from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Vote(Base):
    __tablename__ = "votes"

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
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id"),
        primary_key=True,
    )
    weight: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
