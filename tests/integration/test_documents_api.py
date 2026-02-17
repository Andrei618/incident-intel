"""Integration tests for document API."""

import uuid
from typing import Any

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.document import DocType
from incident_intel.models.service import Service


# ============== POST DOCUMENT ===================
async def test_create_document_success_return_201(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """POST /api/v1/documents created document and returns 201."""
    # Arrange
    payload = {
        "service_id": str(sample_service.id),
        "title": "Test document",
        "content": "Test content",
        "doc_type": "runbook",
    }

    # Act
    response = await client.post("/api/v1/documents", json=payload)

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["service_id"] == str(sample_service.id)
    assert data["title"] == "Test document"
    assert data["content"] == "Test content"
    assert data["doc_type"] == "runbook"
    uuid.UUID(data["id"])  # Validates "id" has a valid UUID format
    assert "created_at" in data


async def test_create_document_with_invalid_serice_id_returns_400(
    client: AsyncClient,
) -> None:
    """POST /api/v1/documents with non-existent service_id returns 400."""
    # Arrange
    payload = {
        "service_id": str(uuid.uuid4()),
        "title": "Test document",
        "content": "Test content",
        "doc_type": "runbook",
    }

    # Act
    response = await client.post("/api/v1/documents", json=payload)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]
    assert str(payload["service_id"]) in data["detail"]


async def test_create_document_missing_required_fields_return_422(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """POST /api/v1/documents without required fields returns 422."""
    # Arrange
    payload = {
        "service_id": str(uuid.uuid4()),
    }

    # Act
    response = await client.post("/api/v1/documents", json=payload)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) == 3  # Missing 3 required fields


async def test_create_document_invalid_doc_type_return_422(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """POST /api/v1/documents created document and returns 201."""
    # Arrange
    payload = {
        "service_id": str(uuid.uuid4()),
        "title": "Test document",
        "content": "Test content",
        "doc_type": "INVALID_DOC_TYPE",
    }

    # Act
    response = await client.post("/api/v1/documents", json=payload)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


# ============== GET DOCUMENT ===================
async def test_get_document_success_return_200(
    client: AsyncClient,
    sample_document: dict[str, Any],
) -> None:
    """GET api/v1/documents/{document_id} gets existing document and returns 200."""
    # Arrange
    document_id = sample_document["id"]

    # Act
    response = await client.get(f"/api/v1/documents/{document_id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == document_id
    assert data["title"] == "Test document"
    assert data["content"] == "Test content"
    assert data["doc_type"] == "runbook"


async def test_get_document_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """GET api/v1/documents/{document_id} with non-existing document returns 404."""
    # Arrange
    document_id = str(uuid.uuid4())

    # Act
    response = await client.get(f"/api/v1/documents/{document_id}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]
    assert document_id in data["detail"]


async def test_get_document_invalid_uuid_returns_422(
    client: AsyncClient,
) -> None:
    """GET api/v1/documents/{document_id} with invalid UUID format returns 422."""
    # Arrange
    invalid_uuid = "INVALID_UUID"

    # Act
    response = await client.get(f"/api/v1/documents/{invalid_uuid}")

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


# ============== UPDATE DOCUMENT ===================
async def test_update_document_success_return_200(
    client: AsyncClient,
    sample_document: dict[str, Any],
) -> None:
    """PUT api/v1/documents/{document_id} update existing document and returns 200."""
    # Arrange
    document_id = sample_document["id"]

    payload = {
        "title": "Updated test document",
        "content": "Updated test content",
        "doc_type": "faq",
    }
    # Act
    response = await client.put(f"/api/v1/documents/{document_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify the updated fields changed
    assert data["title"] == "Updated test document"
    assert data["content"] == "Updated test content"
    assert data["doc_type"] == "faq"
    # Verify unchanged fields stayed the same
    assert data["service_id"] == str(sample_document["service_id"])


async def test_update_document_empty_input_return_unchanged_document(
    client: AsyncClient,
    sample_document: dict[str, Any],
) -> None:
    """PUT api/v1/documents/{document_id} updates with empty input does not change document."""
    # Arrange
    document_id = sample_document["id"]

    # Act
    response = await client.put(f"/api/v1/documents/{document_id}", json={})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Test document"
    assert data["content"] == "Test content"
    assert data["doc_type"] == "runbook"


async def test_update_document_non_existing_returns_404(
    client: AsyncClient,
    sample_document: dict[str, Any],
) -> None:
    """PUT api/v1/documents/{document_id} update non-existing document returns 404."""
    # Arrange
    document_id = str(uuid.uuid4())
    payload = {"title": "Updated title"}

    # Act
    response = await client.put(f"/api/v1/documents/{document_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"]
    assert document_id in data["detail"]


async def test_update_document_invalid_service_id_returns_400(
    client: AsyncClient,
    sample_document: dict[str, Any],
) -> None:
    """PUT api/v1/documents/{document_id} update with invalid service ID returns 400."""
    # Arrange
    document_id = str(sample_document["id"])
    service_id = str(uuid.uuid4())
    payload = {"title": "Updated title", "service_id": service_id}

    # Act
    response = await client.put(f"/api/v1/documents/{document_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data


# ============== GET LIST DOCUMENT ===================
async def test_get_document_list_success_returns_200(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/documents returns list of documents with metadata."""
    # Arrange - create 2 documents
    for title in ("Document 1", "Document 2"):
        await client.post(
            "/api/v1/documents",
            json={
                "service_id": str(sample_service.id),
                "title": title,
                "content": "Test content",
                "doc_type": "runbook",
            },
        )

    # Act
    response = await client.get("/api/v1/documents")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_get_document_list_filter_by_service_id(
    client: AsyncClient,
    sample_service: Service,
    test_session: AsyncSession,
) -> None:
    """GET /api/v1/documents filters documents by service ID."""
    # Arrange
    # Create a second service (first service we get from sample_service)
    service_2 = Service(name="service_2", description="Service 2")
    test_session.add(service_2)
    await test_session.commit()
    await test_session.refresh(service_2)

    # Create 2 documents with different services
    document_1 = await client.post(
        "/api/v1/documents",
        json={
            "service_id": str(sample_service.id),
            "title": "Document 1",
            "content": "Test content",
            "doc_type": "runbook",
        },
    )
    await client.post(
        "/api/v1/documents",
        json={
            "service_id": str(service_2.id),
            "title": "Document 2",
            "content": "Test content",
            "doc_type": "runbook",
        },
    )
    assert document_1.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get(f"/api/v1/documents?service_id={sample_service.id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["service_id"] == str(sample_service.id)


async def test_get_document_list_filter_by_doc_type(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/documents filters documents by doc_type."""
    # Arrange
    for doc_type in ["runbook", "faq"]:
        response = await client.post(
            "/api/v1/documents",
            json={
                "title": "Test document",
                "content": "Test content",
                "doc_type": doc_type,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/documents?doc_type=runbook")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["doc_type"] == "runbook"


async def test_get_document_list_filter_by_title_search(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/documents filters documents by search in title (case-insensitive)."""
    # Arrange
    test_documents = [
        ("Database Backup and Recovery Procedures", DocType.RUNBOOK),
        ("BACKUP Schedule for Production Systems", DocType.POLICY),
        ("Disaster Recovery Planning Template", DocType.GUIDE),
    ]
    for title, doc_type in test_documents:
        response = await client.post(
            "/api/v1/documents",
            json={
                "service_id": str(sample_service.id),
                "title": title,
                "content": "Test content",
                "doc_type": doc_type,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/documents?title_search=backup")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2
    # Verify the matching titles
    matched_titles = {doc["title"] for doc in data["items"]}
    assert "Database Backup and Recovery Procedures" in matched_titles
    assert "BACKUP Schedule for Production Systems" in matched_titles
    # Verify the non-match is excluded
    assert "Disaster Recovery Planning Template" not in matched_titles


async def test_get_document_list_pagination_works(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/documents applies pagination to the document list."""
    # Arrange - create 3 documents
    for title in ("Document 1", "Document 2", "Document 3"):
        response = await client.post(
            "/api/v1/documents",
            json={
                "service_id": str(sample_service.id),
                "title": title,
                "content": "Test content",
                "doc_type": "runbook",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    # Act 1 - first page
    response = await client.get("/api/v1/documents?limit=1&offset=0")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["offset"] == 0

    # Act 2 - second page
    response = await client.get("/api/v1/documents?limit=1&offset=1")

    # Assert 2
    assert response.status_code == status.HTTP_200_OK
    data_2 = response.json()
    assert len(data_2["items"]) == 1
    assert data_2["total"] == 3
    assert data_2["items"][0]["id"] != data["items"][0]["id"]


async def test_get_document_list_empty_returns_empty_items(
    client: AsyncClient,
) -> None:
    """GET /api/v1/documents when zero documents exist return empty items."""
    # Arrange

    # Act
    response = await client.get("/api/v1/documents")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


# ============== DELETE DOCUMENT ===================
async def test_delete_document_returns_204(
    client: AsyncClient,
    sample_document: dict[str, Any],
) -> None:
    """DELETE /api/v1/documents/{document_id} deletes existing document and returns 204."""
    # Arrange
    document_id = sample_document["id"]

    # Act
    response = await client.delete(f"/api/v1/documents/{document_id}")

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_document = await client.get(f"/api/v1/documents/{document_id}")
    assert deleted_document.status_code == status.HTTP_404_NOT_FOUND
    data = deleted_document.json()
    assert "detail" in data
    assert document_id in data["detail"]


async def test_delete_document_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """DELETE /api/v1/documents/{document_id} with non-existing document returns 404."""
    # Arrange
    document_id = str(uuid.uuid4())

    # Act
    response = await client.delete(f"/api/v1/documents/{document_id}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]
    assert document_id in data["detail"]
