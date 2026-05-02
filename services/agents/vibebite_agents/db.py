"""Database session helper for the agents package.

Reuses the API service's SQLAlchemy session factory so the agents and the
HTTP API share a single engine + connection pool. Both packages must be
pip-installed editable (the repo's standard setup):

    pip install -e services/api -e services/agents

The session factory honours ``DATABASE_URL`` from ``Settings`` (defaults to
SQLite at ``services/api/vibebite.db``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.database import get_session_factory

if TYPE_CHECKING:  # pragma: no cover - typing-only re-export
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def get_async_session_factory() -> "async_sessionmaker[AsyncSession]":
    """Return the shared async session factory (cached in ``app.database``)."""
    return get_session_factory()


__all__ = ["get_async_session_factory"]
