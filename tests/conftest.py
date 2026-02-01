"""Fixtures for all tests."""

import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from incident_intel.models.base import Base
from incident_intel.models.service import Service

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/incident_intel_test",
)


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create test database engine and tables."""
    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        # Create vector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Drop all tables first to ensure clean schema
        await conn.run_sync(Base.metadata.drop_all)
        # Drop existing enum types if they exist (cleanup from previous runs)
        await conn.execute(text("DROP TYPE IF EXISTS ticketstatus CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS ticketpriority CASCADE"))
        # Create all tables (this will also create the enum types)
        await conn.run_sync(Base.metadata.create_all)

    # Yield the engine
    yield engine

    # Cleanup: Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Close engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """Fixture for creating session.

    Creates a fresh session for each test.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def sample_service(test_session: AsyncSession) -> Service:
    """Create a sample service for testing tickets.

    Creates a fresh service for each test that needs one.
    """
    # Create a Service instance
    service = Service(name="test-service", description="Test service")

    # Add the Service instance to the session
    test_session.add(service)

    # Commit the transaction
    await test_session.commit()

    # Refresh to get the ID
    await test_session.refresh(service)

    # Return the service
    return service
