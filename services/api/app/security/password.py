from __future__ import annotations

"""Argon2id password hashing.

Wraps `passlib`'s argon2 backend. Passlib auto-selects argon2id, which is
the variant we want (resistant to both side-channel and GPU attacks).
"""

from passlib.context import CryptContext

# `argon2` here resolves to argon2id by default in passlib >= 1.7.4 when the
# argon2-cffi bindings are installed. We pin the scheme list to argon2 so a
# future passlib upgrade can't silently pick a different default.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return an argon2id hash of `password` (includes salt + params)."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time-ish verify; returns False on any verifier error."""
    try:
        return _pwd_context.verify(password, password_hash)
    except Exception:  # noqa: BLE001 - malformed hash should not 500 the route
        return False
