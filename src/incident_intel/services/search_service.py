"""Service layer for search operations."""

import asyncio
import json
import os
import time
from typing import Any
from uuid import UUID

from redis import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import Session
from incident_intel.core.logging import get_logger
from incident_intel.core.redis import redis_client
from incident_intel.services.embedding_service import create_embeddings

logger = get_logger(__name__)

REDIS_TTL = int(os.getenv("REDIS_TTL", "86400"))

K = 60  # Constant for Reciprocal Rank Fusion (RRF) in hybrid_search

MIN_VECTOR_SIMILARITY = float(os.getenv("MIN_VECTOR_SIMILARITY", "0.3"))


async def get_or_create_embeddings(query: str) -> str:
    """Get embedding of user query from Redis cache if exists, call OpenAI, if not.

    Args:
        query: user query.

    Returns:
        Embedding as string (ready for pgvector).
    """
    t_start = time.perf_counter()
    normalized_query = query.lower()
    cache_hit = False
    try:
        embedding_redis = await redis_client.get(normalized_query)
        if embedding_redis:
            cache_hit = True
            result = str(json.loads(embedding_redis))
        else:
            embedding = (await create_embeddings([normalized_query]))[0]
            embedding_redis = json.dumps(embedding)
            await redis_client.set(normalized_query, embedding_redis, ex=REDIS_TTL)
            result = str(embedding)
        logger.info(
            "timing_embedding",
            duration_ms=int((time.perf_counter() - t_start) * 1000),
            cache_hit=cache_hit,
        )
        return result
    except RedisError as e:
        logger.warning("redis_cache_unavailable", action="FALLBACK_TO_OPENAI")
        logger.debug("redis_cache_error_detail", error=e)
        embedding = (await create_embeddings([normalized_query]))[0]
        return str(embedding)


async def keyword_search(
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
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

    return [dict(row) for row in results]


async def vector_search(
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
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
 WHERE 1 - (embedding <=> :embedding) >= :min_similarity
 ORDER BY score DESC LIMIT :limit
"""

    response = await session.execute(
        text(sql),
        {"embedding": embedding, "limit": limit, "min_similarity": MIN_VECTOR_SIMILARITY},
    )
    results = response.mappings().all()
    logger.debug("vector_search_complete", result_count=len(results))

    return [dict(row) for row in results]


async def _keyword_with_own_session(query: str, limit: int) -> list[dict[str, Any]]:
    """Create own session for keyword search."""
    async with Session() as s:
        return await keyword_search(session=s, query=query, limit=limit)


async def _vector_with_own_session(query: str, limit: int) -> list[dict[str, Any]]:
    """Create own session for vector search."""
    async with Session() as s:
        return await vector_search(session=s, query=query, limit=limit)


async def hybrid_search(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Hybrid search combining keyword and vector search."""
    logger.debug("hybrid_search_starting", query=query)

    if query.strip() == "":
        return []

    t_start = time.perf_counter()

    chunk_data: dict[UUID, dict[str, Any]] = {}

    # Use two separate sessions, so each concurrent query gets its own connection.
    keyword_results, vector_results = await asyncio.gather(
        _keyword_with_own_session(query=query, limit=limit),
        _vector_with_own_session(query=query, limit=limit),
    )
    t_search = time.perf_counter()

    for results in (keyword_results, vector_results):
        for rank, row in enumerate(results):
            chunk_id = row["id"]
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = {
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "chunk_index": row["chunk_index"],
                    "score": 0.0,
                }
            chunk_data[chunk_id]["score"] += 1 / (K + rank + 1)  # +1 because enumerate starts at 0

    final_results = sorted(chunk_data.values(), key=lambda x: x["score"], reverse=True)[:limit]
    logger.debug("hybrid_search_complete", result_count=len(final_results))

    logger.info(
        "timing_hybrid_search",
        search_ms=int((t_search - t_start) * 1000),
        total_ms=int((time.perf_counter() - t_start) * 1000),
        keyword_count=len(keyword_results),
        vector_count=len(vector_results),
        final_count=len(final_results),
    )

    return final_results
