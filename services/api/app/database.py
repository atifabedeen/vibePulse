from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings


def make_async_engine(settings: Settings | None = None) -> AsyncEngine:
    """Build an async engine for whatever DATABASE_URL is configured.

    Supports two dialects:
      * Postgres via ``postgresql+psycopg://...`` (psycopg v3, sync+async on
        the same URL)
      * SQLite via ``sqlite+aiosqlite:///./vibebite.db`` (file-based, no
        server required)
    """
    cfg = settings or get_settings()
    url = cfg.async_database_url

    # SQLite ignores most pool kwargs; we keep a small kwarg surface so the
    # same call works for both dialects.
    kwargs: dict = {"echo": False, "future": True}
    if not url.startswith("sqlite"):
        kwargs["pool_pre_ping"] = True

    return create_async_engine(url, **kwargs)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = make_async_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession; commit on success, rollback on exception."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
