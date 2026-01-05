"""Database connection and session management."""

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/incident_intel"
)

ECHO_SQL_VALUE = os.getenv("ECHO_SQL", "false").lower()
ECHO_SQL = {"true": True, "debug": "debug"}.get(ECHO_SQL_VALUE, False)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use; prevents stale connection errors
    echo=ECHO_SQL,  # Controlled by ECHO_SQL env var; logs all SQL when enabled
)


async def check_database_connection() -> bool:
    """Check if database is accessible.

    Returns:
        True if database connection is healthy, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.scalar(text("SELECT 1"))
        return True
    except Exception:
        return False
