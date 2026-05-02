from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `app` importable when invoked from services/api/.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env from repo root so `alembic upgrade head` picks up DATABASE_URL the
# same way the app does. Best-effort: missing dotenv or missing file is fine.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT.parent.parent / ".env")
except ImportError:
    pass

from app.models import Base  # noqa: E402  (path setup must come first)
# Importing the models package registers all tables on Base.metadata.
from app import models  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _to_sync_url(db_url: str) -> str:
    """Strip async driver suffixes so Alembic uses a sync driver.

    Alembic runs migrations synchronously; the app uses the async driver. On
    Postgres both modes share the same `postgresql+psycopg` URL (psycopg v3),
    so we just normalise away `+asyncpg`. On SQLite we drop `+aiosqlite` and
    fall back to the stdlib `sqlite://` driver.
    """
    sync_url = (
        db_url.replace("postgresql+asyncpg", "postgresql+psycopg")
        .replace("postgresql+psycopg_async", "postgresql+psycopg")
    )
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if sync_url.startswith("sqlite+aiosqlite"):
        sync_url = sync_url.replace("sqlite+aiosqlite", "sqlite", 1)
    return sync_url


# Override the URL from the environment if set. Alembic uses the SYNC driver.
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", _to_sync_url(db_url))
else:
    # If the ini file's URL is async-flavoured (e.g. someone set the same
    # value), still coerce to a sync driver here.
    existing = config.get_main_option("sqlalchemy.url")
    if existing:
        config.set_main_option("sqlalchemy.url", _to_sync_url(existing))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Re-emit batch ops on SQLite so column-level alters work portably.
        render_as_batch=(url or "").startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
