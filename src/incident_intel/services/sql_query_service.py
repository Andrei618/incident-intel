"""Service for executing SQL queries against the tickets table.

Converts LLM-extracted intent into parameterized SQL queries.
Only count and list operations are supported — this is not free-form text-to-SQL.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.schemas.classification import (
    SqlAction,
    SQLIntent,
    TicketFilters,
    WhereClause,
)

logger = get_logger(__name__)


def _build_where_clause(filters: TicketFilters) -> WhereClause:
    """Build list of conditions + params dict from non-None filters."""
    conditions = []
    params: dict[str, Any] = {}
    need_join = False

    # Local variables to avoid modifying the caller's object - Pydantic model
    since = filters.since
    until = filters.until
    # Defensive swap to prevent since > until in SQL
    if since is not None and until is not None and since > until:
        since, until = until, since

    if filters.priority is not None:
        conditions.append("t.priority = :priority")
        params["priority"] = filters.priority.value
    if filters.status is not None:
        conditions.append("t.status = :status")
        params["status"] = filters.status.value
    if filters.service_name is not None:
        conditions.append("s.name = :service_name")
        params["service_name"] = filters.service_name
        need_join = True
    if since is not None:
        conditions.append("t.created_at >= :since")
        params["since"] = since
    if until is not None:
        # Exclusive upper bound — LLM uses next-day midnight for inclusive ranges
        conditions.append("t.created_at < :until")
        params["until"] = until

    if conditions:
        return WhereClause(
            sql=f"WHERE {' AND '.join(conditions)}", params=params, needs_join=need_join
        )
    else:
        return WhereClause(sql="", params={}, needs_join=False)


async def query_tickets(session: AsyncSession, intent: SQLIntent) -> str:
    """Query tickets based on the right SQL template and return formatted results."""
    where = _build_where_clause(filters=intent.filters)

    if intent.action == SqlAction.COUNT:
        if where.needs_join:
            base = "SELECT COUNT(*) FROM tickets t JOIN services s ON t.service_id = s.id"
            stmt = f"{base} {where.sql}"
        else:
            base = "SELECT COUNT(*) FROM tickets t"
            stmt = f"{base} {where.sql}"

        logger.debug("query_tickets_count_starting", action=intent.action.value)
        response = await session.execute(text(stmt), where.params)
        result = response.scalar_one()
        logger.debug("query_tickets_count_complete", result_count_value=result)
        return _format_count_result(count=result, filters=intent.filters)
    else:
        base_1 = """
            SELECT t.id, t.title, t.status, t.priority, t.created_at, t.assignee,
            s.name as service_name FROM tickets t JOIN services s ON t.service_id = s.id
        """
        base_2 = "ORDER BY t.created_at DESC LIMIT :limit"
        stmt = f"{base_1} {where.sql} {base_2}"

        where.params["limit"] = intent.limit
        logger.debug("query_tickets_list_starting", action=intent.action.value)
        response = await session.execute(text(stmt), where.params)
        result = response.mappings().all()
        logger.debug("query_tickets_list_complete", result_count=len(result))
        return _format_list_result(rows=result)


def _format_count_result(count: int, filters: TicketFilters) -> str:
    """Build description for COUNT template from non-None filters."""
    description = []

    if filters.priority is not None:
        description.append(f"priority: {filters.priority.value}")
    if filters.status is not None:
        description.append(f"status: {filters.status.value}")
    if filters.service_name is not None:
        description.append(f"service: {filters.service_name}")
    if filters.since is not None:
        description.append(f"since {filters.since}")
    if filters.until is not None:
        description.append(f"until {filters.until}")

    if not description:
        return f"There are {count} tickets in total."
    else:
        return f"There are {count} tickets with {', '.join(description)}."


def _format_list_result(rows: Sequence[RowMapping]) -> str:
    """Build numbered list for LIST template."""
    if not rows:
        return "No tickets found matching your filters."

    list_results = []
    for i, row in enumerate(rows, 1):
        list_results.append(
            f"{i}. [{row['priority']}] {row['title']} - {row['service_name']} ({row['status']}, {row['created_at']})"
        )
    ticket_list = "\n".join(list_results)
    return f"Found {len(rows)} tickets:\n{ticket_list}"
