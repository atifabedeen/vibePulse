from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root `.env` path: services/api/app/config.py -> repo root is parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT_ENV = _REPO_ROOT / ".env"
# Anchor SQLite DB at a fixed absolute path so the same DB is used regardless
# of CWD. RunPod / Postgres overrides this entirely via DATABASE_URL.
_DEFAULT_SQLITE_PATH = _REPO_ROOT / "services" / "api" / "vibebite.db"


class Settings(BaseSettings):
    """Runtime config sourced from environment variables (and optionally `.env`).

    Only includes vars the API service uses today. Other services declare their
    own subsets in their own `config.py`.
    """

    # Connection strings.
    # Default to a file-based SQLite DB so a clean checkout can run with zero
    # external infra. For RunPod / production, override DATABASE_URL with a
    # `postgresql+psycopg://...` URL.
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{_DEFAULT_SQLITE_PATH}",
        description=(
            "DB URL. Defaults to SQLite (aiosqlite) at services/api/vibebite.db "
            "(absolute path; CWD-independent). Override with "
            "`postgresql+psycopg://...` on Postgres/RunPod."
        ),
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Auth
    jwt_secret: str = Field(default="dev-only-not-a-real-secret-change-me")
    jwt_refresh_secret: str = Field(default="dev-only-refresh-secret-change-me")

    # Service identity / observability
    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    service_name: str = Field(default="vibebite-api")

    model_config = SettingsConfigDict(
        # Look at both repo-root .env (preferred) and CWD .env (fallback) so
        # the same code works whether invoked from repo root or services/api/.
        env_file=(str(_REPO_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Async URL for SQLAlchemy's create_async_engine.

        Coerces common alternates so callers can pass either the sync or the
        async form interchangeably.
        """
        url = self.database_url
        # Postgres: psycopg v3 exposes both sync and async on `postgresql+psycopg`.
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        # SQLite: plain `sqlite://` -> `sqlite+aiosqlite://` for async.
        if url.startswith("sqlite://") and not url.startswith("sqlite+"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic / one-shot scripts."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        # Alembic uses the stdlib sqlite3 driver — strip aiosqlite if present.
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite", 1)
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
