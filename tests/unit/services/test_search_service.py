"""Unit tests for search service."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from redis import RedisError

from incident_intel.services.search_service import get_or_create_embeddings, hybrid_search


# ====================== get_or_create_embeddings ===========================
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


# ====================== hybrid_search ===========================
@patch("incident_intel.services.search_service.keyword_search", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.vector_search", new_callable=AsyncMock)
async def test_hybrid_search_return_results(
    mock_vector_search,
    mock_keyword_search,
) -> None:
    """Test hybrid_search return correctly all fields in results."""
    # Arrange
    vector_chunk_id = uuid.uuid4()
    vector_doc_id = uuid.uuid4()
    keyword_chunk_id = uuid.uuid4()
    keyword_doc_id = uuid.uuid4()

    mock_vector_search.return_value = [
        {
            "id": vector_chunk_id,
            "document_id": vector_doc_id,
            "title": "Test vector document",
            "content": "Test vector content",
            "chunk_index": 9,
            "score": 0.9,
        },
    ]
    mock_keyword_search.return_value = [
        {
            "id": keyword_chunk_id,
            "document_id": keyword_doc_id,
            "title": "Test keyword document",
            "content": "Test keyword content",
            "chunk_index": 1,
            "score": 0.1,
        },
    ]
    mock_session = AsyncMock()

    # Act
    results = await hybrid_search(session=mock_session, query="Test query")

    # Assert
    assert len(results) == 2

    vector_results = next(r for r in results if r["id"] == vector_chunk_id)
    assert vector_results["document_id"] == vector_doc_id
    assert vector_results["title"] == "Test vector document"
    assert vector_results["content"] == "Test vector content"
    assert vector_results["chunk_index"] == 9
    assert vector_results["score"] == pytest.approx(
        1 / (60 + 1)
    )  # RRF score for a chunk at rank 1 in one list only

    keyword_results = next(r for r in results if r["id"] == keyword_chunk_id)
    assert keyword_results["score"] == pytest.approx(1 / (60 + 1))


@patch("incident_intel.services.search_service.keyword_search", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.vector_search", new_callable=AsyncMock)
async def test_hybrid_search_overlapping_chunk_scores_higher(
    mock_vector_search,
    mock_keyword_search,
) -> None:
    """Test hybrid_search scores chunk that appears in both (vector and keyword) searches higher."""
    # Arrange
    shared_chunk_id = uuid.uuid4()
    keyword_only_id = uuid.uuid4()
    vector_only_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_keyword_search.return_value = [
        {
            "id": shared_chunk_id,
            "document_id": doc_id,
            "title": "Test document",
            "content": "Test keyword content 1",
            "chunk_index": 12,
            "score": 0.2,
        },
        {
            "id": keyword_only_id,
            "document_id": doc_id,
            "title": "Test document",
            "content": "Test keyword content 2",
            "chunk_index": 34,
            "score": 0.1,
        },
    ]
    mock_vector_search.return_value = [
        {
            "id": shared_chunk_id,
            "document_id": doc_id,
            "title": "Test document",
            "content": "Test vector content 1",
            "chunk_index": 12,
            "score": 0.9,
        },
        {
            "id": vector_only_id,
            "document_id": doc_id,
            "title": "Test document",
            "content": "Test vector content 2",
            "chunk_index": 56,
            "score": 0.8,
        },
    ]
    mock_session = AsyncMock()

    # Act
    results = await hybrid_search(session=mock_session, query="Test query")

    # Assert
    assert len(results) == 3
    assert results[0]["id"] == shared_chunk_id

    shared_chunk_results = next(r for r in results if r["id"] == shared_chunk_id)
    assert shared_chunk_results["score"] == pytest.approx(1 / (60 + 1) + 1 / (60 + 1))

    keyword_only_results = next(r for r in results if r["id"] == keyword_only_id)
    assert keyword_only_results["score"] == pytest.approx(1 / (60 + 2))

    vector_only_results = next(r for r in results if r["id"] == vector_only_id)
    assert vector_only_results["score"] == pytest.approx(1 / (60 + 2))


@patch("incident_intel.services.search_service.keyword_search", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.vector_search", new_callable=AsyncMock)
async def test_hybrid_search_by_empty_query_does_not_call_other_searches(
    mock_vector_search,
    mock_keyword_search,
) -> None:
    """Test hybrid_search does not call keyword_search and vector_search when query is empty."""
    # Arrange
    mock_session = AsyncMock()

    # Act
    results = await hybrid_search(session=mock_session, query="")

    # Assert
    assert len(results) == 0
    mock_keyword_search.assert_not_called()
    mock_vector_search.assert_not_called()


@patch("incident_intel.services.search_service.keyword_search", new_callable=AsyncMock)
@patch("incident_intel.services.search_service.vector_search", new_callable=AsyncMock)
async def test_hybrid_search_respects_limit(
    mock_vector_search,
    mock_keyword_search,
) -> None:
    """Test hybrid_search correctly truncates results to limit even if combined set is larger."""
    # Arrange
    limit = 3
    doc_id = uuid.uuid4()

    # 5 results each, totally disjoint
    mock_keyword_search.return_value = [
        {
            "id": uuid.uuid4(),
            "document_id": doc_id,
            "title": "A",
            "content": f"K{i}",
            "chunk_index": i,
            "score": 0.5,
        }
        for i in range(5)
    ]
    mock_vector_search.return_value = [
        {
            "id": uuid.uuid4(),
            "document_id": doc_id,
            "title": "B",
            "content": f"V{i}",
            "chunk_index": i,
            "score": 0.5,
        }
        for i in range(5)
    ]
    mock_session = AsyncMock()

    # Act
    results = await hybrid_search(session=mock_session, query="Test query", limit=limit)

    # Assert
    assert len(results) == limit  # Should truncate down to 3 from the combined 10
