from __future__ import annotations

"""Auth request/response schemas (sec 7.1).

We don't depend on `pydantic[email]` so the email field is a constrained
str validated by a small regex. The validator is intentionally permissive
(matches RFC 5322 in spirit, not letter); the server lowercases on store.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserOut

# Pragmatic email pattern; full RFC 5322 is not what we need here. We just
# want to reject obvious nonsense like "no-at-sign" or "two@@signs".
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _validate_email(value: str) -> str:
    v = value.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("invalid email")
    return v


class RegisterIn(BaseModel):
    email: str = Field(..., max_length=320)
    password: str = Field(..., min_length=8, max_length=256)
    display_name: str = Field(..., min_length=1, max_length=255)
    avatar_url: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)


class LoginIn(BaseModel):
    email: str = Field(..., max_length=320)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)


class RefreshIn(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """Returned by /register and /login."""

    user: UserOut
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Alias kept for callers expecting a "MeOut" type per the spec list.
MeOut = UserOut
