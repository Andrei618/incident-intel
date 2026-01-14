"""Alembic migration environment configuration.

Configures database connection and model discovery for schema migrations.
Handles async-to-sync driver conversion for compatibility with Alembic's
synchronous migration runner.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to sys.path for model imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from incident_intel.models.base import Base

# Alembic Config object provides access to alembic.ini values
config = context.config

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
# Alembic compares this metadata against the database to detect schema changes
target_metadata = Base.metadata


def get_url() -> str:
    """Retrieve database URL with driver conversion for Alembic compatibility.

    Priority order:
    1. DATABASE_URL environment variable (production/CI)
    2. sqlalchemy.url from alembic.ini (local development)

    Driver conversion:
    - Converts postgresql+asyncpg:// to postgresql+psycopg://
    - Handles legacy postgres:// format from some hosting platforms

    Returns:
        str: Database URL with synchronous driver

    Raises:
        ValueError: If no database URL is configured
    """
    url = os.getenv("DATABASE_URL")
    if url:
        # Convert async driver to sync for Alembic
        url = url.replace("+asyncpg", "+psycopg")

        # Handle legacy postgres:// prefix
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    # Fallback to alembic.ini configuration
    fallback_url = config.get_main_option("sqlalchemy.url")
    if not fallback_url:
        raise ValueError(
            "Database URL not found. Set DATABASE_URL env var or sqlalchemy.url in alembic.ini"
        )
    return fallback_url


def run_migrations_offline() -> None:
    """Run migrations in offline mode.

    Generates SQL script without connecting to database.
    Useful for generating migration scripts for manual review or execution.

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode.

    Connects to database and applies migrations directly.
    Uses NullPool for connection management to avoid connection pooling
    overhead in short-lived migration scripts.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
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
