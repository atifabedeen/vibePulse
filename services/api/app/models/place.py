from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Float,
    Index,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Place(Base):
    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    google_place_id: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    address: Mapped[str | None] = mapped_column(nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    price_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    user_rating_ct: Mapped[int | None] = mapped_column(nullable=True)

    cuisines: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    raw_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    vibe_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "price_level BETWEEN 0 AND 4",
            name="places_price_level_check",
        ),
        Index("places_google_id_idx", "google_place_id"),
        Index("places_expires_idx", "expires_at"),
        # The ivfflat index is created in the migration directly (op.execute)
        # because it needs the operator class clause which the ORM Index
        # doesn't express well.
    )
