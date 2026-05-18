"""Fixtures for all tests."""

import os
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from incident_intel.core.database import get_session
from incident_intel.llm.provider import ChatMessage
from incident_intel.main import app
from incident_intel.models.base import Base
from incident_intel.models.service import Service
from incident_intel.schemas.classification import QueryIntent

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
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Fixture for creating session.

    Creates a fresh session for each test.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
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


@pytest.fixture
async def client(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient]:
    """Create HTTP client with test database override."""

    # Create override function
    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        session_factory = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_factory() as session:
            yield session

    # Tell FastAPI to use override instead of real get_session
    app.dependency_overrides[get_session] = override_get_session

    # Create async HTTP client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Cleanup - remove only "get_session" override after test (not all overrides)
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
async def sample_ticket(
    client: AsyncClient,
    sample_service: Service,
) -> dict[str, Any]:
    """Create a sample ticket for testing GET/UPDATE/DELETE operations.

    Returns the created ticket as a dict (JSON response from POST).
    """
    payload = {
        "service_id": str(sample_service.id),
        "title": "Test ticket",
        "description": "Sample ticket for integration tests",
        "priority": "p1",
        "assignee": "Test assignee",
        "reporter": "Test reporter",
    }
    response = await client.post("/api/v1/tickets", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()  # type: ignore[no-any-return]


@pytest.fixture
async def sample_document(
    client: AsyncClient,
    sample_service: Service,
) -> dict[str, Any]:
    """Create a sample document for testing GET/UPDATE/DELETE operations.

    Returns:
        Created document as a dict (JSON response from POST).
    """
    payload = {
        "service_id": str(sample_service.id),
        "title": "Test document",
        "content": "Test content",
        "doc_type": "runbook",
    }
    response = await client.post("/api/v1/documents", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def mock_create_embeddings():
    """Mock OpenAI embeddings to avoid real API calls in tests."""

    async def fake_embeddings(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]

    with (
        patch(
            "incident_intel.services.document_service.create_embeddings",
            side_effect=fake_embeddings,
        ),
        patch(
            "incident_intel.services.search_service.create_embeddings",
            side_effect=fake_embeddings,
        ) as mock,
    ):
        yield mock


@pytest.fixture(autouse=True)
def mock_redis_client():
    """Mock Redis client to always response with empty cache.

    Empty cache in response leads to calling embedding for user query (also mocked).
    """
    with (
        patch(
            "incident_intel.services.search_service.redis_client.get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "incident_intel.services.search_service.redis_client.set",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield


@pytest.fixture
def mock_classify():
    """Mock classify_query function."""
    intent = QueryIntent(route="hybrid", confidence=0.9, document_query="test query")
    with patch("incident_intel.services.chat_service.classify_query", return_value=intent):
        yield intent


@pytest.fixture
def mock_chat_provider():
    """Mock OpenAI provider."""
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value="Test answer from LLM.")

    test_message = ["Hello", " world"]

    async def mock_async_gen(**kwargs: list[ChatMessage]) -> AsyncIterator[str]:
        for token in test_message:
            yield token

    mock.generate_stream = mock_async_gen

    with patch("incident_intel.services.chat_service.OpenAIChatProvider", return_value=mock):
        yield mock


@pytest.fixture
def mock_search_session(test_engine):
    """Creat session from engine and patch Session with it.

    Workaround till implementation issue #40 "Refactor search_service to accept session parameter".
    """
    test_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    with patch("incident_intel.services.search_service.Session", test_session_factory):
        yield
