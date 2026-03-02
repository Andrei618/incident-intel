"""API endpoints for search in documents."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import get_session
from incident_intel.schemas.search import Method, SearchResponse, SearchResultItem
from incident_intel.services.search_service import hybrid_search, keyword_search, vector_search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max amount of search results"),
    method: Method = Query(Method.HYBRID, description="Method query parameter"),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Search document chunks using keyword, vector, or hybrid similarity."""
    response: list[dict[str, Any]]
    if method == Method.KEYWORD:
        response = await keyword_search(session=session, query=q, limit=limit)
    elif method == Method.VECTOR:
        response = await vector_search(session=session, query=q, limit=limit)
    else:
        response = await hybrid_search(session=session, query=q, limit=limit)

    mapped_response = [
        SearchResultItem(
            chunk_id=row["id"],
            document_id=row["document_id"],
            document_title=row["title"],
            content=row["content"],
            chunk_index=row["chunk_index"],
            score=row["score"],
        )
        for row in response
    ]

    return SearchResponse(items=mapped_response, query=q, total=len(mapped_response), method=method)
