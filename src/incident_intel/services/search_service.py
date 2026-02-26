"""Service layer for search operations."""

import json
import os
from collections.abc import Sequence

from redis import RedisError
from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.core.redis import redis_client
from incident_intel.services.embedding_service import create_embeddings

logger = get_logger(__name__)

REDIS_TTL = int(os.getenv("REDIS_TTL", "86400"))


async def get_or_create_embeddings(query: str) -> str:
    """Get embedding of user query from Redis cache if exists, call OpenAI, if not.

    Args:
        query: user query.

    Returns:
        Embedding as string (ready for pgvector).
    """
    normalized_query = query.lower()
    try:
        embedding_redis = await redis_client.get(normalized_query)
        if embedding_redis:
            return str(json.loads(embedding_redis))
        else:
            embedding = (await create_embeddings([normalized_query]))[0]
            embedding_redis = json.dumps(embedding)
            await redis_client.set(normalized_query, embedding_redis, ex=REDIS_TTL)
            return str(embedding)
    except RedisError as e:
        logger.warning("redis_cache_unavailable", action="FALLBACK_TO_OPENAI")
        logger.debug("redis_cache_error_detail", error=e)
        embedding = (await create_embeddings([normalized_query]))[0]
        return str(embedding)


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
    embedding = await get_or_create_embeddings(query)

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
