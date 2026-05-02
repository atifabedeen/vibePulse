from __future__ import annotations

"""/api/v1/auth — register, login, refresh, logout, me (sec 7.1)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.user import User
from app.schemas.auth import (
    AccessTokenOut,
    LoginIn,
    MeOut,
    RefreshIn,
    RegisterIn,
    TokenPair,
)
from app.security.deps import get_current_user
from app.security.jwt import (
    InvalidTokenError,
    create_access_token,
    decode_token,
)
from app.services.auth_service import (
    authenticate,
    create_user,
    email_exists,
    issue_token_pair,
)

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterIn,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """Create a new account. 409 if the email is already taken
    (case-insensitive), 400 if validation fails (Pydantic does that for us)."""
    if await email_exists(session, body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        )
    try:
        user = await create_user(
            session,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            avatar_url=body.avatar_url,
        )
    except IntegrityError:
        # Race: another request created the same email between our check and
        # the flush. Map to the same 409 the explicit check would have raised.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        )

    access, refresh = issue_token_pair(user.id)
    return TokenPair(
        user=MeOut.model_validate(user),
        access_token=access,
        refresh_token=refresh,
    )


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginIn,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    user = await authenticate(session, email=body.email, password=body.password)
    if user is None:
        # Same 401 for "no such user" and "bad password" — don't leak
        # which case applied (helps against email enumeration).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        )
    access, refresh = issue_token_pair(user.id)
    return TokenPair(
        user=MeOut.model_validate(user),
        access_token=access,
        refresh_token=refresh,
    )


@router.post("/refresh", response_model=AccessTokenOut)
async def refresh_token(body: RefreshIn) -> AccessTokenOut:
    """Mint a new access token from a valid refresh token. Refresh-token
    rotation (sec 11.1) is deferred to a later milestone — for now the
    refresh token continues to be valid until its 30-day expiry."""
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired refresh token",
        )
    new_access = create_access_token(payload["sub"])
    return AccessTokenOut(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_user: User = Depends(get_current_user)) -> None:
    """Stub — token revocation is a later concern (sec 11.1 mentions
    refresh-hash storage; not implemented yet). The client should drop
    its tokens on receipt of 204."""
    return None


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut.model_validate(user)
