"""Unit tests for embedding service."""

from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from incident_intel.services.embedding_service import chunk_text, create_embeddings


# ============== chunk_text ===================
def test_chunk_text_long_text_returns_multiple_chunks() -> None:
    """Test chunk_text text longer than chunk_size returns multiple chunks."""
    # Arrange
    content = "Timeout errors in payment-service logs: connection pool exhausted"
    chunk_size = 4
    chunk_overlap = 1

    # Act
    chunks = chunk_text(
        content=content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Assert
    assert len(chunks) == 4
    assert chunks[0] == "Timeout errors in payment"


def test_chunk_text_short_text_returns_one_chunk() -> None:
    """Test chunk_text text shorter than chunk_size returns exactly 1 chunk."""
    # Arrange
    content = "The server crashed"
    chunk_size = 100
    chunk_overlap = 0

    # Act
    chunks = chunk_text(
        content=content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Assert
    assert len(chunks) == 1
    assert chunks[0] == "The server crashed"


def test_chunk_text_empty_text_returns_empty_list() -> None:
    """Test chunk_text empty text return empty list."""
    # Arrange
    content = ""
    chunk_size = 4
    chunk_overlap = 1

    # Act
    chunks = chunk_text(
        content=content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Assert
    assert len(chunks) == 0


def test_chunk_text_overlap_works() -> None:
    """Test chunk_text overlapin text appears in two chunks."""
    # Arrange
    content = "Timeout errors in payment-service logs: connection pool exhausted"
    chunk_size = 4
    chunk_overlap = 1

    # Act
    chunks = chunk_text(
        content=content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Assert
    assert len(chunks) == 4
    assert "payment" in chunks[0]
    assert "payment" in chunks[1]


# ============== create_embeddings ===================
@patch("incident_intel.services.embedding_service.client")
async def test_create_embeddings_three_texts_returns_three_embedding_vectors(mock_client) -> None:
    """Test create_embeddings with three chunks of text returns three embedding vectors."""
    # Arrange
    mock_items = [
        MagicMock(embedding=[0.1, 0.2]),
        MagicMock(embedding=[0.3, 0.4]),
        MagicMock(embedding=[0.5, 0.6]),
    ]
    mock_response = MagicMock(data=mock_items)
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    # Act
    result = await create_embeddings(["text_1", "text_2", "text_3"])

    # Assert
    assert len(result) == 3
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]
    assert result[2] == [0.5, 0.6]


@patch("incident_intel.services.embedding_service.client")
async def test_create_embeddings_one_text_returns_one_embedding_vector(mock_client) -> None:
    """Test create_embeddings with one chunk of text returns one embedding vector."""
    # Arrange
    mock_items = [
        MagicMock(embedding=[0.1, 0.2]),
    ]
    mock_response = MagicMock(data=mock_items)
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    # Act
    result = await create_embeddings(["text_1"])

    # Assert
    assert len(result) == 1
    assert result[0] == [0.1, 0.2]


@patch("incident_intel.services.embedding_service.client")
async def test_create_embeddings_api_error_returns_authentication_error(mock_client) -> None:
    """Test create_embeddings with API error returns AuthentificationError."""
    # Arrange
    mock_client.embeddings.create = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
    )

    # Act + Assert
    with pytest.raises(openai.AuthenticationError):
        await create_embeddings(["test_1"])
