"""Integration tests for document search."""

from uuid import UUID

from fastapi import status
from httpx import AsyncClient


async def test_search_returns_matching_chunks(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=kubernetes finds matching chunks and returns 200."""
    # Arrange
    payload = {
        "title": "Test document",
        "content": "Kubernetes pod crash loop",
        "doc_type": "runbook",
    }
    response_create = await client.post("/api/v1/documents", json=payload)
    assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=kubernetes")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    assert UUID(data["items"][0]["chunk_id"])
    assert UUID(data["items"][0]["document_id"])
    assert data["items"][0]["document_title"] == "Test document"
    assert "kubernetes" in data["items"][0]["content"].lower()
    assert data["items"][0]["chunk_index"] == 0
    assert data["items"][0]["score"] > 0


async def test_search_returns_empty_for_no_matches(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=quantum physics returns empty response and 200."""
    # Arrange
    payload = {
        "title": "Test document",
        "content": "Kubernetes pod crash loop",
        "doc_type": "runbook",
    }
    response_create = await client.post("/api/v1/documents", json=payload)
    assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=quantum physics")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0


async def test_search_respects_limit(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&limit=... returns one or less results and 200."""
    # Arrange
    contents = (
        "Kubernetes pod crash loop 1",
        "Kubernetes pod crash loop 2",
        "Kubernetes pod crash loop 3",
    )

    for content in contents:
        response_create = await client.post(
            "/api/v1/documents",
            json={
                "title": "Test document",
                "content": content,
                "doc_type": "runbook",
            },
        )
        assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=kubernetes&limit=1")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1


async def test_search_missing_query_422(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search (no q param) returns error and 422."""
    # Act
    response = await client.get("/api/v1/search")

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


async def test_search_empty_query_422(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q= returns error and 422."""
    # Act
    response = await client.get("/api/v1/search?q=")

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


async def test_search_results_ordered_by_score(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=database result with more mentions of keyword has higher score."""
    # Arrange
    contents = (
        "database database database database database",
        "database",
    )

    for content in contents:
        response_create = await client.post(
            "/api/v1/documents",
            json={
                "title": "Test document",
                "content": content,
                "doc_type": "runbook",
            },
        )
        assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=database")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) >= 2
    assert data["items"][0]["score"] > data["items"][1]["score"]
