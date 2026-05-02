from __future__ import annotations

"""User-facing pydantic schemas.

`UserOut` is the public representation we expose; `password_hash` and
`deleted_at` are intentionally absent. ORM-mode (`from_attributes=True`)
lets routes return SQLAlchemy User objects directly.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """PATCH /users/me body. All fields optional; only provided fields update."""

    display_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    avatar_url: Optional[str] = Field(default=None, max_length=2048)
