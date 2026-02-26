"""Unit tests for search service."""

import json
from unittest.mock import AsyncMock, patch

from redis import RedisError

from incident_intel.services.search_service import get_or_create_embeddings


@patch("incident_intel.services.search_service.redis_client.get", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.redis_client.set", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.create_embeddings", new_callable=AsyncMock)
async def test_get_or_create_embeddings_cache_hit_returns_cached_embedding(
    mock_create_embedding,
    mock_redis_client_set,
    mock_redis_client_get,
) -> None:
    """Test get_or_create_embeddings return JSON string of an embedding."""
    # Arrange
    mock_redis_client_get.return_value = json.dumps([0.1, 0.2])

    # Act
    result = await get_or_create_embeddings("test query")

    # Assert
    assert result == str([0.1, 0.2])
    mock_create_embedding.assert_not_called()
    mock_redis_client_set.assert_not_called()


@patch("incident_intel.services.search_service.redis_client.get", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.redis_client.set", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.create_embeddings", new_callable=AsyncMock)
async def test_get_or_create_embeddings_cache_miss_returns_new_embedding(
    mock_create_embedding,
    mock_redis_client_set,
    mock_redis_client_get,
) -> None:
    """Test get_or_create_embeddings return JSON string of an embedding."""
    # Arrange
    mock_redis_client_get.return_value = None
    mock_create_embedding.return_value = [[0.1, 0.2]]

    # Act
    result = await get_or_create_embeddings("test query")

    # Assert
    assert result == str([0.1, 0.2])
    mock_redis_client_set.assert_called_with("test query", json.dumps([0.1, 0.2]), ex=86400)


@patch("incident_intel.services.search_service.redis_client.get", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.redis_client.set", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.create_embeddings", new_callable=AsyncMock)
async def test_get_or_create_embeddings_redis_down_falls_back_to_openai(
    mock_create_embedding,
    mock_redis_client_set,
    mock_redis_client_get,
) -> None:
    """Test get_or_create_embeddings falls back to OpenAI when Redis is down."""
    # Arrange
    mock_redis_client_get.side_effect = RedisError
    mock_create_embedding.return_value = [[0.1, 0.2]]

    # Act
    result = await get_or_create_embeddings("test query")

    # Assert
    assert result == str([0.1, 0.2])
    mock_create_embedding.assert_called_once()
    mock_redis_client_set.assert_not_called()
