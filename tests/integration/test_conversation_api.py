"""Integration tests for conversation."""

import uuid

import pytest
from fastapi import status
from httpx import AsyncClient


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
