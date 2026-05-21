"""Integration tests for document search."""

from math import sqrt
from unittest.mock import patch
from uuid import UUID

from fastapi import status
from httpx import AsyncClient

from incident_intel.services.search_service import MIN_VECTOR_SIMILARITY


# Custom embeddings for testing vector search
async def custom_embeddings(texts: list[str]) -> list[list[float]]:
    """Override the mock fixture (mock_create_embeddings) to receive different embeddings.

    Example:
        When search for something like "server connection issues"
        (no keyword match to either, hits the else branch)
        — result vector [0.85, 0.1, ...] is closer to the "networking" vector [0.9, 0.1, ...]
        than the "database" vector [0.1, 0.9, ...]
    """
    results = []
    for text in texts:
        if "networking" in text.lower():
            # Vector A: [0.9, 0.1, 0.1, ...]
            results.append([0.9] + [0.1] * 1535)
        elif "database" in text.lower():
            # Vector B: [0.1, 0.9, 0.1, ...]
            results.append([0.1, 0.9] + [0.1] * 1534)
        else:
            # Query vector — close to "networking" vector
            results.append([0.85] + [0.1] * 1535)
    return results


# ============== shared validation ===================
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


# ============== keyword_search ===================
async def test_keyword_search_returns_matching_chunks(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&method=keyword finds matching chunks and returns 200."""
    # Arrange
    payload = {
        "title": "Test document",
        "content": "Kubernetes pod crash loop",
        "doc_type": "runbook",
    }
    response_create = await client.post("/api/v1/documents", json=payload)
    assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=kubernetes&method=keyword")

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
    assert data["method"] == "keyword"


async def test_keyword_search_returns_empty_for_no_matches(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&method=keyword (no matched query) returns empty response and 200."""
    # Arrange
    payload = {
        "title": "Test document",
        "content": "Kubernetes pod crash loop",
        "doc_type": "runbook",
    }
    response_create = await client.post("/api/v1/documents", json=payload)
    assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=quantum physics&method=keyword")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0


async def test_keyword_search_respects_limit(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&limit=...&method=keyword returns one or less results and 200."""
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
    response = await client.get("/api/v1/search?q=kubernetes&limit=1&method=keyword")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1


async def test_keyword_search_results_ordered_by_score(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&method=keyword result with more mentions of keyword has higher score."""
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
    response = await client.get("/api/v1/search?q=database&method=keyword")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) >= 2
    assert data["items"][0]["score"] > data["items"][1]["score"]


# ============== vector_search ===================
async def test_vector_search_returns_matching_chunks(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&method=vector finds matching chunks and returns 200."""
    # Arrange
    payload = {
        "title": "Test document",
        "content": "Kubernetes pod crash loop",
        "doc_type": "runbook",
    }
    response_create = await client.post("/api/v1/documents", json=payload)
    assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/search?q=kubernetes&method=vector")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    assert data["items"][0]["document_title"] == "Test document"
    assert data["items"][0]["score"] > 0
    assert data["method"] == "vector"


async def test_vector_search_respects_limit(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&limit=...&method=vector returns one or less results and 200."""
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
    response = await client.get("/api/v1/search?q=kubernetes&limit=1&method=vector")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1


async def test_vector_search_semantic_matches(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&method=vector finds matching chunks by semantic and returns 200.

    Vector search finds results even when there are no shared keywords between query and content.
    """
    # Arrange
    payload = {
        "title": "Test document",
        "content": "Kubernetes pod restart troubleshooting",
        "doc_type": "runbook",
    }
    response_create = await client.post("/api/v1/documents", json=payload)
    assert response_create.status_code == status.HTTP_201_CREATED

    # Act
    response_keyword_search = await client.get("/api/v1/search?q=container&method=keyword")
    response_vector_search = await client.get("/api/v1/search?q=container&method=vector")

    # Assert
    # Keyword search
    assert response_keyword_search.status_code == status.HTTP_200_OK
    data_keyword_search = response_keyword_search.json()
    assert data_keyword_search["total"] == 0

    # Vector search
    assert response_vector_search.status_code == status.HTTP_200_OK
    data_vector_search = response_vector_search.json()
    assert data_vector_search["total"] >= 1


async def test_vector_search_ranks_by_similarity(
    client: AsyncClient,
) -> None:
    """GET /api/v1/search?q=...&method=vector sorts matching chunks by semantic score and returns 200."""
    # Arrange
    with (
        patch(
            "incident_intel.services.document_service.create_embeddings",
            side_effect=custom_embeddings,
        ),
        patch(
            "incident_intel.services.search_service.create_embeddings",
            side_effect=custom_embeddings,
        ),
    ):
        payload_doc_1 = {
            "title": "Test document 1",
            "content": "networking troubleshooting",
            "doc_type": "runbook",
        }
        payload_doc_2 = {
            "title": "Test document 2",
            "content": "database optimization",
            "doc_type": "runbook",
        }

        response_create_doc_1 = await client.post("/api/v1/documents", json=payload_doc_1)
        response_create_doc_2 = await client.post("/api/v1/documents", json=payload_doc_2)

        assert response_create_doc_1.status_code == status.HTTP_201_CREATED
        assert response_create_doc_2.status_code == status.HTTP_201_CREATED

        # Act
        response_search = await client.get(
            "/api/v1/search?q=server connection issues&method=vector"
        )

    # Assert
    assert response_search.status_code == status.HTTP_200_OK
    data = response_search.json()
    assert data["total"] == 2
    assert data["items"][0]["document_title"] == "Test document 1"
    assert data["items"][0]["score"] > data["items"][1]["score"]


async def test_vector_search_excludes_results_below_threshold(
    client: AsyncClient,
) -> None:
    """Vector search excludes chunks whose cosine similarity is below MIN_VECTOR_SIMILARITY.

    Constructs two unit-magnitude vectors with known cosine similarity to a fixed query
    vector — one just above the threshold (kept), one just below (filtered).
    """
    # Arrange
    above = MIN_VECTOR_SIMILARITY + 0.05
    below = MIN_VECTOR_SIMILARITY - 0.05

    async def threshold_test_embeddings(texts: list[str]) -> list[list[float]]:
        """Route embedding requests to vectors with controlled cosine similarity to the query.

        Query vector q = [1.0, 0, 0, ..., 0] is fixed. For unit-magnitude vectors with
        first component v[0] and zeros elsewhere except v[1] = sqrt(1 - v[0]**2), the
        cosine similarity to q equals v[0]. So routing on the keyword sets the score
        exactly to `above` or `below`.

        Texts containing 'above' → cosine = MIN_VECTOR_SIMILARITY + 0.05 (passes filter).
        Texts containing 'below' → cosine = MIN_VECTOR_SIMILARITY - 0.05 (filtered out).
        Anything else (e.g. the search query) → query vector itself.
        """
        results = []
        for text in texts:
            if "above" in text.lower():
                # Unit vector with cosine = `above` to the query
                results.append([above, sqrt(1 - above**2)] + [0.0] * 1534)
            elif "below" in text.lower():
                # Unit vector with cosine = `below` to the query
                results.append([below, sqrt(1 - below**2)] + [0.0] * 1534)
            else:
                # Query vector q = [1.0, 0, 0, ..., 0] — unit vector pointing along the first axis
                results.append([1.0] + [0.0] * 1535)
        return results

    with (
        patch(
            "incident_intel.services.document_service.create_embeddings",
            side_effect=threshold_test_embeddings,
        ),
        patch(
            "incident_intel.services.search_service.create_embeddings",
            side_effect=threshold_test_embeddings,
        ),
    ):
        payload_doc_1 = {
            "title": "above",
            "content": "above marker",
            "doc_type": "runbook",
        }
        payload_doc_2 = {
            "title": "below",
            "content": "below marker",
            "doc_type": "runbook",
        }

        response_create_doc_1 = await client.post("/api/v1/documents", json=payload_doc_1)
        response_create_doc_2 = await client.post("/api/v1/documents", json=payload_doc_2)

        assert response_create_doc_1.status_code == status.HTTP_201_CREATED
        assert response_create_doc_2.status_code == status.HTTP_201_CREATED

        # Act
        response_search = await client.get("/api/v1/search?q=server connection issue&method=vector")

    # Assert
    assert response_search.status_code == status.HTTP_200_OK
    data = response_search.json()
    assert data["total"] == 1
    assert data["items"][0]["document_title"] == "above"
