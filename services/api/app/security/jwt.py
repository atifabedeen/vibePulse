from __future__ import annotations

"""JWT helpers for access + refresh tokens.

Spec (sec 11.1):
  * Access token: 15 min, HS256, signed with `settings.jwt_secret`.
  * Refresh token: 30 days, HS256, signed with `settings.jwt_refresh_secret`.
  * Payload: {sub: user_id, exp, iat, type: "access"|"refresh"}.

The two-secret split means a leaked access secret cannot mint refresh
tokens (and vice versa); rotating the refresh secret on a security event
invalidates all sessions without invalidating short-lived access tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal, Any

from jose import JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)

TokenType = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    """Raised when a JWT fails validation (signature, expiry, type, etc.)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode(sub: str, token_type: TokenType, secret: str, ttl: timedelta) -> str:
    issued = _now()
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": int(issued.timestamp()),
        "exp": int((issued + ttl).timestamp()),
        "type": token_type,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _encode(user_id, "access", get_settings().jwt_secret, ACCESS_TOKEN_TTL)


def create_refresh_token(user_id: str) -> str:
    return _encode(
        user_id, "refresh", get_settings().jwt_refresh_secret, REFRESH_TOKEN_TTL
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode + validate a JWT. Raises `InvalidTokenError` on any failure.

    Picks the secret based on `expected_type` so an attacker can't pass a
    refresh token where an access token is required (or vice versa).
    """
    secret = (
        get_settings().jwt_secret
        if expected_type == "access"
        else get_settings().jwt_refresh_secret
    )
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(
            f"wrong token type: expected {expected_type}, got {payload.get('type')!r}"
        )
    if not payload.get("sub"):
        raise InvalidTokenError("token missing sub")
    return payload
