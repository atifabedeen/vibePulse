from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Place(Base):
    __tablename__ = "places"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    google_place_id: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    address: Mapped[Optional[str]] = mapped_column(nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    price_level: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Numeric(2, 1), nullable=True)
    user_rating_ct: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Portable list-of-strings via SQLAlchemy generic JSON. Maps to JSONB on
    # Postgres and TEXT on SQLite.
    cuisines: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_blob: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Embedding stored as JSON list-of-floats for portability. We'll specialise
    # this to pgvector at query-time once embeddings are wired up; for the bare
    # CRUD path JSON works on both Postgres and SQLite.
    vibe_embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "price_level BETWEEN 0 AND 4",
            name="places_price_level_check",
        ),
        Index("places_google_id_idx", "google_place_id"),
        Index("places_expires_idx", "expires_at"),
        # The ivfflat index is created Postgres-only inside the migration —
        # SQLAlchemy's Index can't express the pgvector operator class clause.
    )
