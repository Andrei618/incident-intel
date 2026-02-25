"""Service layer for search operations."""

from collections.abc import Sequence

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.services.embedding_service import create_embeddings

logger = get_logger(__name__)


async def keyword_search(
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> Sequence[RowMapping]:
    """Find list of chunks matching the query.

    Args:
        session: Active database session.
        query: Raw SQL query for searching chunks where content_tsv matches plainto_tsquery.
               Uses parametrized query preventing SQL injections.
        limit: max number of search result.

    Returns:
        Dict-like result of query representing list of chunks.
    """
    logger.debug("keyword_search_starting", query=query)

    if query.strip() == "":
        return []

    sql = """\
SELECT dc.id, dc.document_id, d.title, dc.content, dc.chunk_index,
 ts_rank(dc.content_tsv, plainto_tsquery('english', :query)) AS score
 FROM document_chunks dc JOIN documents d ON dc.document_id = d.id
 WHERE dc.content_tsv @@ plainto_tsquery('english', :query)
 ORDER BY score DESC LIMIT :limit
"""
    response = await session.execute(text(sql), {"query": query, "limit": limit})
    results = response.mappings().all()
    logger.debug("keyword_search_complete", result_count=len(results))

    return results


async def vector_search(
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> Sequence[RowMapping]:
    """Semantic similarity search using pgvector on document chunk embeddings.

    Args:
        session: Active database session.
        query: search text from user.
        limit: max number of search result.

    Returns:
        Dict-like result of query representing list of chunks.
    """
    logger.debug("vector_search_starting", query=query)

    if query.strip() == "":
        return []

    # str() -> pgvector expects the embedding parameter as a string representation of the vector
    embedding = str((await create_embeddings([query]))[0])

    # 1 - cosine_distance = cosine_similarity (higher = more relevant)
    sql = """\
SELECT dc.id, dc.document_id, d.title, dc.content, dc.chunk_index,
 1 - (embedding <=> :embedding) AS score
 FROM document_chunks dc JOIN documents d ON dc.document_id = d.id
 ORDER BY score DESC LIMIT :limit
"""

    response = await session.execute(text(sql), {"embedding": embedding, "limit": limit})
    results = response.mappings().all()
    logger.debug("vector_search_complete", result_count=len(results))

    return results
