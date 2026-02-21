"""Integration tests for document embeddings."""

from typing import Any
from uuid import UUID

from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.document import DocumentChunk
from incident_intel.models.service import Service


async def test_document_embeddings_post_creates_chunks(
    client: AsyncClient,
    sample_service: Service,
    test_session: AsyncSession,
) -> None:
    """POST /api/v1/documents created document, chunks and returns 201."""
    # Arrange
    payload = {
        "service_id": str(sample_service.id),
        "title": "Test document",
        "content": "Timeout errors in payment-service logs: connection pool exhausted",
        "doc_type": "runbook",
    }

    # Act
    response = await client.post("/api/v1/documents", json=payload)

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    stmt = select(DocumentChunk).where(DocumentChunk.document_id == UUID(data["id"]))
    stmt = stmt.order_by(DocumentChunk.chunk_index)
    result = await test_session.execute(stmt)
    chunks = list(result.scalars().all())

    assert len(chunks) >= 1
    assert isinstance(chunks[0].id, UUID)
    assert chunks[0].document_id == UUID(data["id"])
    assert chunks[0].content.startswith("Timeout")
    assert len(chunks[0].embedding) == 1536
    assert chunks[0].chunk_index == 0


async def test_document_embeddings_put_with_content_recreate_chunks(
    client: AsyncClient,
    sample_document: dict[str, Any],
    test_session: AsyncSession,
) -> None:
    """PUT /api/v1/documents/{document_id} with content update existing document, re-create chunks and returns 200."""
    # Arrange
    document_id = sample_document["id"]

    stmt_1 = select(DocumentChunk).where(DocumentChunk.document_id == UUID(document_id))
    stmt_1 = stmt_1.order_by(DocumentChunk.chunk_index)
    result_1 = await test_session.execute(stmt_1)
    chunks_1 = list(result_1.scalars().all())

    payload = {
        "content": "Timeout errors in payment-service logs: connection pool exhausted",
    }

    # Act
    response = await client.put(f"/api/v1/documents/{document_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    stmt_2 = select(DocumentChunk).where(DocumentChunk.document_id == UUID(data["id"]))
    stmt_2 = stmt_2.order_by(DocumentChunk.chunk_index)
    result_2 = await test_session.execute(stmt_2)
    chunks_2 = list(result_2.scalars().all())

    assert chunks_1[0].content.startswith("Test")
    assert chunks_2[0].content.startswith("Timeout")
    assert chunks_2[0].id != chunks_1[0].id


async def test_document_embeddings_put_without_content_keep_chunks_unchanged(
    client: AsyncClient,
    sample_document: dict[str, Any],
    test_session: AsyncSession,
) -> None:
    """PUT /api/v1/documents/{document_id} without content update existing document, does not re-create chunks and returns 200."""
    # Arrange
    document_id = sample_document["id"]

    stmt_1 = select(DocumentChunk).where(DocumentChunk.document_id == UUID(document_id))
    stmt_1 = stmt_1.order_by(DocumentChunk.chunk_index)
    result_1 = await test_session.execute(stmt_1)
    chunks_1 = list(result_1.scalars().all())

    payload = {"title": "Updated title"}

    # Act
    response = await client.put(f"/api/v1/documents/{document_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    stmt_2 = select(DocumentChunk).where(DocumentChunk.document_id == UUID(data["id"]))
    stmt_2 = stmt_2.order_by(DocumentChunk.chunk_index)
    result_2 = await test_session.execute(stmt_2)
    chunks_2 = list(result_2.scalars().all())

    assert chunks_1[0].content.startswith("Test")
    assert chunks_2[0].content.startswith("Test")
    assert chunks_2[0].id == chunks_1[0].id


async def test_document_embeddings_delete_removes_all_chunks(
    client: AsyncClient,
    sample_document: dict[str, Any],
    test_session: AsyncSession,
) -> None:
    """DELETE /api/v1/documents/{document_id} removes document and all chunks, returns 204."""
    # Arrange
    document_id = sample_document["id"]

    # Act
    response = await client.delete(f"/api/v1/documents/{document_id}")

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    stmt = select(DocumentChunk).where(DocumentChunk.document_id == UUID(document_id))
    stmt = stmt.order_by(DocumentChunk.chunk_index)
    result = await test_session.execute(stmt)
    chunks = list(result.scalars().all())

    assert len(chunks) == 0
