"""Database connection and session management."""

import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

raw = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/incident_intel"
)
parts = urlsplit(raw)
pairs = parse_qsl(parts.query, keep_blank_values=True)
sslmode = dict(pairs).get("sslmode")
query = [(k, v) for k, v in pairs if k != "sslmode"]
raw = urlunsplit(parts._replace(query=urlencode(query)))

if raw.startswith("postgres://"):
    raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw.startswith("postgresql://") and "+" not in raw.split("://", 1)[0]:
    raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = raw

ECHO_SQL_VALUE = os.getenv("ECHO_SQL", "false").lower()
ECHO_SQL = {"true": True, "debug": "debug"}.get(ECHO_SQL_VALUE, False)

connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "server_settings": {"application_name": "incident-intel-api"},
}
if sslmode:
    connect_args["ssl"] = sslmode
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use; prevents stale connection errors
    echo=ECHO_SQL,  # Controlled by ECHO_SQL env var; logs all SQL when enabled
    connect_args=connect_args,
)

# Async session factory for FastAPI routes
Session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Required for async - prevents implicit refresh after commit
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency for database sessions.

    Yields a session that is automatically closed after request.
    Usage: session: AsyncSession = Depends(get_session)
    """
    async with Session() as session:
        yield session


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
