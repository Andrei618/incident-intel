"""Integration tests for chat."""

import json
import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incident_intel.llm.provider import ChatMessage
from incident_intel.schemas.classification import QueryIntent


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


async def test_chat_empty_message_422(
    client: AsyncClient,
) -> None:
    """POST /api/v1/chat empty message returns error and 422."""
    # Pydantic min_length=1 rejects empty string → 422
    # Arrange + Act
    response = await client.post("/api/v1/chat", json={"message": ""})

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


async def test_chat_invalid_conversation_id_404(
    client: AsyncClient,
) -> None:
    """POST /api/v1/chat non-existent UUID message returns ConversationNotFoundError and 404."""
    # Non-existent UUID → ConversationNotFoundError → HTTP 404
    # Arrange
    test_conversation_id = uuid.uuid4()

    # Act
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "test message",
            "conversation_id": str(test_conversation_id),
        },
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data


async def test_chat_creates_conversation_and_returns_answer(
    client: AsyncClient,
    mock_classify,
    mock_chat_provider,
    sample_document,
    mock_search_session,
) -> None:
    """POST /api/v1/chat with no conversation_id creates conversation and returns correct answer and 200."""
    # Happy path: POST with no conversation_id, get back 200 with conversation_id,
    # message_id, answer, route_used, confidence
    # Arrange + Act
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "test message",
        },
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    uuid.UUID(data["conversation_id"])
    uuid.UUID(data["message_id"])
    assert data["answer"] == "Test answer from LLM."
    assert "sources" in data
    assert data["route_used"] == "hybrid"
    assert data["confidence"] == 0.9


async def test_chat_include_sources_false_filters_sources(
    client: AsyncClient,
    mock_classify,
    mock_chat_provider,
    sample_document,
    mock_search_session,
) -> None:
    """POST /api/v1/chat with include_sources=False does not return sources."""
    # Same happy path but options.include_sources=False → sources: [] in response
    # Arrange + Act
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "test message",
            "options": {
                "include_sources": False,
            },
        },
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["sources"] == []


async def test_chat_stream_returns_sse_events(
    client: AsyncClient,
    mock_classify,
    mock_chat_provider,
    sample_document,
    mock_search_session,
) -> None:
    """POST /api/v1/chat with stream=True yields token events and done event with correct shape."""
    # stream: true → response has content-type: text/event-stream, yields token events
    # + done event with correct shape
    # Arrange + Act
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "test message",
            "stream": True,
        },
    )
    lines = [line for line in response.text.strip().split("\n") if line.startswith("data:")]
    tokens = [json.loads(line.removeprefix("data: ")) for line in lines]

    # Assert
    assert response.headers["content-type"].startswith("text/event-stream")  # returns SSE, not JSON
    assert tokens[0]["content"] == "Hello"
    assert tokens[1]["content"] == " world"
    assert tokens[-1]["type"] == "done"
    uuid.UUID(tokens[-1]["conversation_id"])
    uuid.UUID(tokens[-1]["message_id"])
    assert "sources" in tokens[-1]
    assert tokens[-1]["route_used"] == "hybrid"
    assert tokens[-1]["confidence"] == 0.9


async def test_chat_stream_invalid_conversation_id_returns_error_event(
    client: AsyncClient,
) -> None:
    """POST /api/v1/chat with stream=True and invalid conversation_id yields SSE error event."""
    # stream: true with bad UUID → yields SSE error event
    # (not HTTP 404 — different behavior from non-streaming)
    # Arrange
    test_conversation_id = uuid.uuid4()

    # Act
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "test message",
            "conversation_id": str(test_conversation_id),
            "stream": True,
        },
    )
    lines = [line for line in response.text.strip().split("\n") if line.startswith("data:")]
    tokens = [json.loads(line.removeprefix("data: ")) for line in lines]

    # Assert
    assert response.headers["content-type"].startswith("text/event-stream")
    assert tokens[0]["type"] == "error"
    assert str(test_conversation_id) in tokens[0]["message"]
