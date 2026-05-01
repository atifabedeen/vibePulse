from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a transactional AsyncSession.

    Commits on a clean exit; rolls back on any exception raised by the route
    handler. Routes should not call `session.commit()` themselves.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
