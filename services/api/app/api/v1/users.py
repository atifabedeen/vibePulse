from __future__ import annotations

"""/api/v1/users — profile update + DSR delete (sec 7.2 + 11.5)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate
from app.security.deps import get_current_user
from app.services.auth_service import scrub_user

router = APIRouter(tags=["users"])


@router.patch("/me", response_model=UserOut)
async def patch_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    """Update the caller's profile. Pydantic v2's `model_dump(exclude_unset=True)`
    means a missing field never overwrites the stored value; we only touch
    fields the client explicitly sent (including explicit `null`)."""
    data = body.model_dump(exclude_unset=True)
    if "display_name" in data and data["display_name"] is not None:
        user.display_name = data["display_name"]
    if "avatar_url" in data:
        # Allow setting to null to clear an avatar.
        user.avatar_url = data["avatar_url"]
    session.add(user)
    await session.flush()
    return UserOut.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """DSR endpoint (sec 11.5). Scrubs PII and sets `deleted_at`. Foreign
    keys to this user remain valid so analytics/agent_runs don't break;
    they just point at a tombstone row that can no longer re-identify."""
    scrub_user(user)
    session.add(user)
    await session.flush()
    return None
