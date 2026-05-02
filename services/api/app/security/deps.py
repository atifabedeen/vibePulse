from __future__ import annotations

"""FastAPI dependency: resolve `Authorization: Bearer <jwt>` to a User row.

A 401 is raised for any of: missing header, malformed header, expired or
invalid signature, wrong token type, or user not found / soft-deleted.
We deliberately keep the error messages generic so we don't leak which
of those reasons applied.

This module also provides mission-scoped authz helpers:
  * `get_mission_member` — verifies the resolved user belongs to the
    `mission_members` row for the path `mission_id`.
  * `get_mission_owner`  — same as above but additionally requires
    `role='owner'`.
Both yield the `MissionMember` row so handlers can read role/joined_at.
"""

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.mission import Mission, MissionMember
from app.models.user import User
from app.security.jwt import InvalidTokenError, decode_token


_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="not a member of this mission",
)
_OWNER_ONLY = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="owner role required",
)
_MISSION_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="mission not found",
)


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise _UNAUTHORIZED
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _UNAUTHORIZED
    return parts[1].strip()


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError:
        raise _UNAUTHORIZED

    user_id = payload["sub"]
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.deleted_at is not None:
        raise _UNAUTHORIZED
    return user


async def get_mission_member(
    mission_id: str = Path(..., description="Mission UUID from the path"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MissionMember:
    """Verify `user` is in `mission_members` for the path `mission_id`.

    404 if the mission does not exist; 403 if it exists but the caller is
    not a member. Returns the `MissionMember` row so the handler can
    branch on `role`.
    """
    mission = (
        await session.execute(select(Mission).where(Mission.id == mission_id))
    ).scalar_one_or_none()
    if mission is None:
        raise _MISSION_NOT_FOUND

    member = (
        await session.execute(
            select(MissionMember).where(
                MissionMember.mission_id == mission_id,
                MissionMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise _FORBIDDEN
    return member


async def get_mission_owner(
    member: MissionMember = Depends(get_mission_member),
) -> MissionMember:
    """Same as `get_mission_member` plus a `role='owner'` check."""
    if member.role != "owner":
        raise _OWNER_ONLY
    return member
