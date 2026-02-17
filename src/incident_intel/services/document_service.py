"""Service layer for document operations."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ColumnElement

from incident_intel.core.logging import get_logger
from incident_intel.exceptions import DocumentNotFoundError, ServiceNotFoundError
from incident_intel.models.document import DocType, Document
from incident_intel.schemas.document import DocumentCreate, DocumentUpdate

logger = get_logger(__name__)


async def create_document(
    session: AsyncSession,
    data: DocumentCreate,
) -> Document:
    """Create a new document.

    Args:
        session: Active database session.
        data: Validated document creation data.

    Returns:
        Created document with generated ID and timestamps.

    Raises:
        ServiceNotFoundError: If service_id does not exist.
        HTTPException: 400 if data violate business rules constraints.
    """
    # Production-safe: identifiers only, no PII
    logger.info(
        "document_creating",
        service_id=str(data.service_id) if data.service_id else None,
        doc_type=str(data.doc_type),
    )
    # Development only: includes user content for debugging
    logger.debug(
        "document_creating_detail",
        title=data.title,
        service_id=str(data.service_id) if data.service_id else None,
        doc_type=str(data.doc_type),
    )

    document_dict = data.model_dump()
    new_document = Document(**document_dict)

    session.add(new_document)

    try:
        await session.commit()
        await session.refresh(new_document)  # Reload to get the generated ID
        logger.info("document_created", document_id=str(new_document.id))
    except IntegrityError as e:
        await session.rollback()
        error_msg = str(e.orig)
        logger.error(
            "document_creation_failed",
            doc_type=str(data.doc_type),
            error_type=type(e).__name__,
        )
        logger.debug("document_creation_failed_detail", error=str(e))

        if "fk_documents_service_id_services" in error_msg:
            # Type narrowing: FK violation guarantees service_id is not None.
            # Why it's needed: ServiceNotFoundError expects UUID, not UUID | None.
            if data.service_id is None:
                raise ValueError(
                    "FK constraint violation with None service_id - this should never happen"
                ) from e
            raise ServiceNotFoundError(data.service_id) from e

        # TODO Replace all HTTPExceptions with domain exceptions in service layer.
        # Related issue - #16.
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data: constraint violation",
            ) from e

    return new_document


async def get_document(
    session: AsyncSession,
    document_id: UUID,
) -> Document:
    """Get a document by ID.

    Args:
        session: Active database session.
        document_id: UUID of document to retrieve.

    Returns:
        The requested document.

    Raises:
        DocumentNotFoundError: If document does not exist.
    """
    logger.debug("document_fetching", document_id=str(document_id))

    stmt = select(Document).where(Document.id == document_id)
    document = await session.scalar(stmt)

    if document is None:
        logger.warning("document_not_found", document_id=str(document_id))
        raise DocumentNotFoundError(document_id)

    logger.debug("document_found", document_id=str(document_id))
    return document


async def update_document(
    session: AsyncSession,
    document_id: UUID,
    update_data: DocumentUpdate,
) -> Document:
    """Update an existing document.

    Args:
        session: Active database session.
        document_id: UUID of document to update.
        update_data: Fields to update (partial updates supported).

    Returns:
        Updated document.

    Raises:
        DocumentNotFoundError: If document does not exist.
        HTTPException: 400 if data violates business rules constraints.
    """
    # Get existing document
    document = await get_document(session, document_id)

    # Extract only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return document
    logger.info(
        "document_updating",
        document_id=str(document_id),
        fields=list(update_dict.keys()),
    )

    logger.debug(
        "document_updating_detail",
        document_id=str(document_id),
        fields=list(update_dict.keys()),
        title=update_dict.get("title"),
    )

    # Apply updates to document object
    for field, value in update_dict.items():
        setattr(document, field, value)

    # Commit with error handling
    try:
        await session.commit()
        await session.refresh(document)
        logger.info("document_updated", document_id=str(document_id))

    except IntegrityError as e:
        await session.rollback()
        error_msg = str(e.orig)
        logger.error(
            "document_update_failed",
            document_id=str(document_id),
            fields=list(update_dict.keys()),
            error_type=type(e).__name__,
        )
        logger.debug("document_update_failed_detail", error=error_msg)

        if "fk_documents_service_id_services" in error_msg:
            # Type narrowing: FK violation guarantees service_id is not None.
            # Why it's needed: ServiceNotFoundError expects UUID, not UUID | None.
            if update_data.service_id is None:
                raise ValueError(
                    "FK constraint violation with None service_id - this should never happen"
                ) from e
            raise ServiceNotFoundError(update_data.service_id) from e
        # TODO Replace all HTTPExceptions with domain exceptions in service layer.
        # Related issue - #16.
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data: constraint violation",
            ) from e

    return document


async def list_documents(
    session: AsyncSession,
    service_id: UUID | None = None,
    doc_type: DocType | None = None,
    title_search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Document], int]:
    """List documents with optional filters and pagination.

    Args:
        session: Active database session.
        service_id: Filter by service ID (optional).
        doc_type: Filter by document type (optional).
        title_search: Search in document title (case-insensitive, optional).
        limit: Maximum number of documents to return (default: 20).
        offset: Number of documents to skip (default: 0).

    Returns:
        Tuple of (list of documents, total count matching filters).

    Example:
    >>> documents, total = await list_documents(
    ...     session,
    ...     doc_type=DocType.RUNBOOK,
    ...     limit=10
    ... )
    >>> print(f"Found {total} documents, showing first 10")
    """
    # Build filter conditions
    filters: list[ColumnElement[bool]] = []
    log_meta: dict[str, str] = {}  # for logging filter conditions applied
    if service_id is not None:
        filters.append(Document.service_id == service_id)
        log_meta["service_id"] = str(service_id)
    if doc_type is not None:
        filters.append(Document.doc_type == doc_type)
        log_meta["doc_type"] = doc_type.value
    if title_search:  # Falsy for None, "". Ignores empty strings.
        filters.append(Document.title.ilike(f"%{title_search}%"))
        log_meta["title_search"] = title_search

    # Main query
    stmt = select(Document).where(*filters)
    stmt = stmt.order_by(Document.created_at.desc(), Document.id.desc())
    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    documents = list(result.scalars().all())

    # Count query
    count_stmt = select(func.count()).select_from(Document).where(*filters)
    total = await session.scalar(count_stmt) or 0

    logger.debug(
        "documents_listed",
        count=len(documents),
        total=total,
        **log_meta,
    )

    return documents, total


async def delete_document(
    session: AsyncSession,
    document_id: UUID,
) -> None:
    """Delete document by ID.

    Args:
        session: Active database session.
        document_id: UUID of the document to delete.

    Raises:
        DocumentNotFoundError: If document does not exist.

    Note:
        Sprint 2: Basic delete (removes document only).
        Sprint 3 TODO: Cleanup document_chunks when chunking is implemented.
    """
    logger.info("document_deleting", document_id=str(document_id))

    # Verify document exists (raises DocumentNotFoundError if not found)
    document = await get_document(session, document_id)

    # Delete document
    await session.delete(document)
    await session.commit()

    logger.info("document_deleted", document_id=str(document_id))
