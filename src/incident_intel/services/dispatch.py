"""Service for routing classified user queries to handlers.

Maps route strings to handler functions that produce context for the LLM chat prompt.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.schemas.classification import DispatchResult, QueryIntent
from incident_intel.services.search_service import hybrid_search
from incident_intel.services.sql_query_service import query_tickets

logger = get_logger(__name__)


async def _sql_handler(
    session: AsyncSession,
    intent: QueryIntent,
    original_query: str,
    limit: int,
) -> DispatchResult:
    """Call ticket table."""
    if intent.sql_intent is None:
        return await _hybrid_handler(
            session=session,
            intent=intent,
            original_query=original_query,
            limit=limit,
        )

    context = await query_tickets(session=session, intent=intent.sql_intent)
    return DispatchResult(context=context, sources=[], route="sql")


async def _hybrid_handler(
    session: AsyncSession,
    intent: QueryIntent,
    original_query: str,
    limit: int,
) -> DispatchResult:
    """Call hybrid search."""
    raw_chunks = await hybrid_search(
        query=intent.document_query or original_query,
        limit=limit,
    )
    numbered_chunks = []
    for i, chunk in enumerate(raw_chunks, 1):
        numbered_chunks.append(f"{i}. Title: {chunk['title']}, content: {chunk['content']}")
    return DispatchResult(context="\n".join(numbered_chunks), sources=raw_chunks, route="hybrid")


async def _clarify_handler(
    session: AsyncSession,
    intent: QueryIntent,
    original_query: str,
    limit: int,
) -> DispatchResult:
    """Return clarifying question."""
    context = intent.clarify_question or "Could you be more specific about what you're looking for?"
    return DispatchResult(context=context, sources=[], route="clarify")


_HANDLERS = {
    "sql": _sql_handler,
    "hybrid": _hybrid_handler,
    "clarify": _clarify_handler,
}


async def dispatch(
    session: AsyncSession,
    intent: QueryIntent,
    original_query: str,
    limit: int = 5,
) -> DispatchResult:
    """Routes classified queries to the appropriate handler.

    Args:
        session: Active database session for SQL/search queries.
        intent: Classification result (sql/hybrid/clarify) of user query.
        original_query: The user's original question text. Used as fallback
                       search query when intent.document_query is None.
        limit: Max chunks to retrieve for hybrid search.

    Returns:
        DispatchResult with context text, source metadata, and actual route used.
    """
    handler = _HANDLERS.get(intent.route)
    if handler is None:
        logger.error("dispatch_receives_unknown_route", route=intent.route)
        handler = _hybrid_handler

    result = await handler(
        session=session,
        intent=intent,
        original_query=original_query,
        limit=limit,
    )
    logger.info("dispatch_complete", route=result.route, source_count=len(result.sources))
    return result
