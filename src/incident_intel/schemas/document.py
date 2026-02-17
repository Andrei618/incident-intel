"""Pydantic schema for documents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incident_intel.models.document import DocType


class DocumentCreate(BaseModel):
    """Request schema for creating a new document.

    User provides: title, content, doc_type, service_id (optional).
    Database auto-generates: id, created_at.
    Background service later generates: chunks + embeddings.
    """

    service_id: UUID | None = Field(
        None,
        description="UUID of the IT-service this document related to",
        examples=[None],
    )
    title: str = Field(
        ...,
        max_length=255,
        description="Document title",
    )
    content: str = Field(..., description="Content of the document")
    doc_type: DocType = Field(
        ...,
        description="Document type",
        examples=["runbook", "policy", "guide", "faq"],
    )


class DocumentUpdate(BaseModel):
    """Request schema for updating a existing document.

    User provides: title, content, doc_type, service_id (all fields optional).
    Database auto-generates: updated_at.
    Background service later generates (if content is updated): chunks + embeddings.
    """

    service_id: UUID | None = Field(
        None,
        description="UUID of the IT-service this document related to",
        examples=[None],
    )
    title: str | None = Field(
        None,
        max_length=255,
        description="Document title",
    )
    content: str | None = Field(
        None,
        min_length=1,  # ?
        description="Content of the document",
    )
    doc_type: DocType | None = Field(
        None,
        description="Document type",
        examples=["runbook", "policy", "guide", "faq"],
    )


class DocumentResponse(BaseModel):
    """Response schema for document metadata.

    Excludes 'content' field for performance.
    Used in document list.
    """

    id: UUID
    service_id: UUID | None
    title: str
    doc_type: DocType
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(BaseModel):
    """Response schema for full document details.

    Includes the full 'content' field.
    Used for single document retrieval.
    """

    id: UUID
    service_id: UUID | None
    title: str
    content: str
    doc_type: DocType
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Response schema for paginated document list."""

    items: list[DocumentResponse]
    total: int = Field(
        ...,
        description="Total number of documents matching filters",
    )
    limit: int = Field(
        ...,
        description="Maximum items per page",
    )
    offset: int = Field(
        ...,
        description="Number of items skipped",
    )
