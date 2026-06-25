"""Integration tests for conversation."""

import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.conversation import Conversation, Message, MessageRole
from incident_intel.models.document import DocType, Document, DocumentChunk
from incident_intel.models.query_log import QueryLog, Route
from incident_intel.models.query_source import QuerySource


@pytest.fixture
async def sample_conversation_id(
    client: AsyncClient,
    mock_classify,
    mock_chat_provider,
    sample_document,
    mock_search_session,
) -> uuid.UUID:
    """Create sample conversation for testing conversations, returns conversation_id."""
    response = await client.post("/api/v1/chat", json={"message": "test message"})
    assert response.status_code == status.HTTP_200_OK
    return response.json()["conversation_id"]


async def test_list_conversations_returns_conversation_list(
    sample_conversation_id: uuid.UUID,
    client: AsyncClient,
) -> None:
    """GET /api/v1/conversations returns a conversation list."""
    # Act
    response = await client.get("/api/v1/conversations")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(item["id"] == str(sample_conversation_id) for item in data["items"])


async def test_get_conversation_returns_detail_conversation(
    sample_conversation_id: uuid.UUID,
    client: AsyncClient,
) -> None:
    """GET /api/v1/conversations/{id} returns detail conversation by ID."""
    # Act
    response = await client.get(f"/api/v1/conversations/{sample_conversation_id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["messages"][0]["content"] == "test message"
    assert data["id"] == str(sample_conversation_id)
    assistant_messages = [m for m in data["messages"] if m["role"] == "assistant"]
    assert len(assistant_messages) == 1
    assistant_msg = assistant_messages[0]
    assert "sources" in assistant_msg
    assert isinstance(assistant_msg["sources"], list)


async def test_get_conversation_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """GET /api/v1/conversations/{id} with non-existing conversation return 404."""
    # Act
    response = await client.get(f"/api/v1/conversations/{uuid.uuid4()}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"]


async def test_get_conversation_filters_system_messages(
    sample_conversation_id: uuid.UUID,
    test_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """GET /api/v1/conversations/{id} excludes system messages from response."""
    # Arrange
    system_message = Message(
        conversation_id=sample_conversation_id,
        role=MessageRole.SYSTEM,
        content="internal system prompt",
    )
    test_session.add(system_message)
    await test_session.commit()

    # Act
    response = await client.get(f"/api/v1/conversations/{sample_conversation_id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all([msg["role"] != "system" for msg in data["messages"]])
    assert len(data["messages"]) > 0


async def test_get_conversation_sorts_sources_by_rank(
    test_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """GET /api/v1/conversations/{id} returns an assistant message's sources ordered by rank ascending."""
    # Arrange
    conversation = Conversation()

    document = Document(
        title="Test title", content="Test document content", doc_type=DocType.RUNBOOK
    )

    chunk_a = DocumentChunk(document=document, content="Test chunk_a content", chunk_index=0)
    chunk_b = DocumentChunk(document=document, content="Test chunk_b content", chunk_index=1)
    chunk_c = DocumentChunk(document=document, content="Test chunk_c content", chunk_index=2)

    message = Message(
        conversation=conversation, role=MessageRole.ASSISTANT, content="Test message content"
    )

    query_log = QueryLog(
        conversation=conversation,
        query_text="Test query text",
        message=message,
        route_used=Route.HYBRID,
        latency_ms=0,
    )
    # insertion order a, b, c but ranks 3, 1, 2 — so the test fails if the relationship isn't ordered.
    QuerySource(
        query_log=query_log,
        document_chunk=chunk_a,
        rank=3,
        relevance_score=0.1,
        was_used=True,
    )
    QuerySource(
        query_log=query_log,
        document_chunk=chunk_b,
        rank=1,
        relevance_score=0.9,
        was_used=True,
    )
    QuerySource(
        query_log=query_log,
        document_chunk=chunk_c,
        rank=2,
        relevance_score=0.5,
        was_used=True,
    )
    test_session.add(conversation)
    await test_session.commit()

    # Act
    response = await client.get(f"/api/v1/conversations/{conversation.id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assistant_messages = [m for m in data["messages"] if m["role"] == "assistant"]
    assistant_msg = assistant_messages[0]
    sources = assistant_msg["sources"]
    returned = [s["chunk_id"] for s in sources]

    # rank-ascending → b(1), c(2), a(3)
    assert returned == [str(chunk_b.id), str(chunk_c.id), str(chunk_a.id)]


async def test_delete_conversation_returns_204(
    sample_conversation_id: uuid.UUID,
    client: AsyncClient,
) -> None:
    """DELETE /api/v1/conversations/{id} delete existing conversation and returns 204."""
    # Act
    response = await client.delete(f"/api/v1/conversations/{sample_conversation_id}")

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT


async def test_delete_conversation_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """DELETE /api/v1/conversations/{id} with non-existing conversation return 404."""
    # Act
    response = await client.delete(f"/api/v1/conversations/{uuid.uuid4()}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"]
