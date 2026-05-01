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

from app.models import Base  # noqa: E402  (path setup must come first)
# Importing the models package registers all tables on Base.metadata.
from app import models  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the URL from the environment if set. Alembic uses the SYNC driver.
db_url = os.getenv("DATABASE_URL")
if db_url:
    # If the app passed an async URL (postgresql+psycopg_async or +asyncpg),
    # coerce to the sync psycopg v3 driver for migrations.
    sync_url = (
        db_url.replace("postgresql+asyncpg", "postgresql+psycopg")
        .replace("postgresql+psycopg_async", "postgresql+psycopg")
    )
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg://", 1)
    config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
