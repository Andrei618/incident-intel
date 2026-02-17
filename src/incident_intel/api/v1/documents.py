"""API endpoints for document management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import get_session
from incident_intel.exceptions import DocumentNotFoundError, ServiceNotFoundError
from incident_intel.models.document import DocType, Document
from incident_intel.schemas.document import (
    DocumentCreate,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
)
from incident_intel.services.document_service import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_document_endpoint(
    document: DocumentCreate,
    session: AsyncSession = Depends(get_session),
) -> Document:
    """Create a new document.

    Raises:
        HTTPException (400) if service_id not found: FK constraint violation.
    """
    try:
        return await create_document(
            data=document,
            session=session,
        )
    except ServiceNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_endpoint(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Document:
    """Get document by ID.

    Raises:
        HTTPException (404) if document not found.
    """
    try:
        return await get_document(
            document_id=document_id,
            session=session,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{document_id}", response_model=DocumentDetailResponse)
async def update_document_endpoint(
    document_id: UUID,
    update_data: DocumentUpdate,
    session: AsyncSession = Depends(get_session),
) -> Document:
    """Update document by ID. Accepts partial updates.

    Raises:
        HTTPException (404) if document not found.
        HTTPException (400) if service_id not found (FK violation)
    """
    try:
        return await update_document(
            document_id=document_id,
            update_data=update_data,
            session=session,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ServiceNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=DocumentListResponse)
async def list_documents_endpoint(
    service_id: UUID | None = Query(None, description="Filter by service ID"),
    doc_type: DocType | None = Query(None, description="Filter by document type"),
    title_search: str | None = Query(
        None, description="Search in document title (case-insensitive)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip"),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    """List documents with optional filters and pagination.

    Return:
        DocumentListResponse: Paginated list of documents with metadata.
    """
    documents, total = await list_documents(
        service_id=service_id,
        doc_type=doc_type,
        title_search=title_search,
        limit=limit,
        offset=offset,
        session=session,
    )
    return DocumentListResponse(
        # Conversion list[Document] -> list[DocumentResponse].
        # Without explicit conversion, mypy --strict complains about error.
        items=[DocumentResponse.model_validate(document) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete document by ID.

    Raises:
        HTTPException (404) if document not found.
    """
    try:
        await delete_document(
            document_id=document_id,
            session=session,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
