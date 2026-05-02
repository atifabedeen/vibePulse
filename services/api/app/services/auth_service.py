from __future__ import annotations

"""Auth business logic.

Routes in `app/api/v1/auth.py` are thin shells over these functions so
the same logic is reusable from the MCP server (sec 9). Anything DB- or
secret-related lives here, not in the route handler.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.security.jwt import create_access_token, create_refresh_token
from app.security.password import hash_password, verify_password


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Case-insensitive lookup. We store emails lowercased, but compare with
    `lower()` defensively in case some path bypassed normalization."""
    needle = email.strip().lower()
    result = await session.execute(
        select(User).where(func.lower(User.email) == needle)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def email_exists(session: AsyncSession, email: str) -> bool:
    """Used by /register pre-check. Treats soft-deleted rows as still taken
    (they hold the email tombstone slot until the GDPR purge job runs)."""
    return (await get_user_by_email(session, email)) is not None


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    avatar_url: Optional[str] = None,
) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=hash_password(password),
        display_name=display_name,
        avatar_url=avatar_url,
    )
    session.add(user)
    # Flush so the row gets its UUID/created_at populated and any unique
    # constraint violation surfaces here (caller maps to 409).
    await session.flush()
    return user


async def authenticate(
    session: AsyncSession, *, email: str, password: str
) -> Optional[User]:
    """Returns the User on success, or None on bad creds / soft-deleted user."""
    user = await get_user_by_email(session, email)
    if user is None or user.deleted_at is not None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def issue_token_pair(user_id: str) -> tuple[str, str]:
    """Mint (access, refresh) for `user_id`."""
    return create_access_token(user_id), create_refresh_token(user_id)


# DSR scrubbing. Email gets a unique tombstone so the unique constraint
# survives even if multiple users delete on the same day.
def scrub_user(user: User) -> None:
    user.email = f"deleted-{user.id}@tombstone.invalid"
    user.display_name = "[deleted]"
    user.avatar_url = None
    user.deleted_at = _utcnow()
