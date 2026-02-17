"""Document and DocumentChunk models for RAG system."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from incident_intel.models.query_source import QuerySource
    from incident_intel.models.service import Service
    from incident_intel.models.ticket_document import TicketDocument

EMBEDDING_DIMENSION = 1536


class DocType(str, enum.Enum):
    """Document types."""

    RUNBOOK = "runbook"
    POLICY = "policy"
    GUIDE = "guide"
    FAQ = "faq"


class Document(Base, TimestampMixin):
    """Global document entity.

    Documents may relate to services, but may not belong to them.
    Documents contain chunks (entities of class DocumentChunk).
    """

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('RUNBOOK', 'POLICY', 'GUIDE', 'FAQ')",
            name="valid_doc_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("services.id", ondelete="SET NULL"),
        index=True,
        default=None,
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[DocType] = mapped_column(
        SQLEnum(
            DocType,
            native_enum=False,
            validate_strings=True,
            # to prevent auto-creation of a CHECK constraint by SQLEnum (we already have CheckConstraint)
            create_constraint=False,
        ),
    )

    # Relationships
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",  # Maintain chunk sequence order
    )
    service: Mapped["Service | None"] = relationship(
        back_populates="documents",
        lazy="selectin",
    )
    ticket_documents: Mapped[list["TicketDocument"]] = relationship(
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    """Chunk of document for embedding and full-text search.

    Vector similarity index (HNSW for fast approximate search).
    Full-text search index for BM25 keyword matching.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        # Unique constraint
        UniqueConstraint("document_id", "chunk_index"),
        # HNSW index for vector similarity
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # Note: GIN index on content_tsv (GENERATED column) will be created via migration
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        default=None,
    )
    chunk_index: Mapped[int] = mapped_column()
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        back_populates="document_chunks",
        lazy="selectin",
    )
    query_sources: Mapped[list["QuerySource"]] = relationship(
        back_populates="document_chunk",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
