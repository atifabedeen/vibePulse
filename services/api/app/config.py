from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config sourced from environment variables (and optionally `.env`).

    Only includes vars the API service uses today. Other services declare their
    own subsets in their own `config.py`.
    """

    # Connection strings
    database_url: str = Field(
        default="postgresql+psycopg://vibebite:vibebite@localhost:5432/vibebite",
        description="Postgres URL. psycopg v3 driver works for both sync (alembic) and async.",
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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Async URL for SQLAlchemy's create_async_engine.

        psycopg v3 exposes the async driver via the `postgresql+psycopg` URL
        with the engine in async mode. Coerce common alternates here too.
        """
        url = self.database_url
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic / one-shot scripts."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
