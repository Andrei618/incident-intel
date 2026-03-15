"""Pydantic schemas for classification of user questions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from incident_intel.models.ticket import TicketPriority, TicketStatus


class SqlAction(str, Enum):
    """Type of SQL query to execute against tickets table.

    Supports two actions on tickets:
    - count: Count tickets matching filters.
    - list: List tickets matching filters.
    """

    COUNT = "count"
    LIST = "list"


class TicketFilters(BaseModel):
    """Filters extracted by LLM from user's natural language question.

    The fields since/until are ISO datetime strings extracted by the LLM.
    OpenAI `response_format` does not enforce format, datetime fields are treated as plain strings.
    Date filters apply to created_at only.
    """

    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    service_name: str | None = None
    since: datetime | None = None
    until: datetime | None = None


class SQLIntent(BaseModel):
    """Input contract for a SQL ticket query.

    Validators ge/le are Pydantic-only. OpenAI `response_format` doesn't enforce them.
    Pydantic validation runs on `.parsed`, so invalid values will raise `ValidationError`
    """

    action: SqlAction
    filters: TicketFilters = Field(default_factory=TicketFilters)
    limit: int = Field(default=10, ge=1, le=100)


class QueryIntent(BaseModel):
    """Classification result from the LLM.

    Route values:
    - "sql": Quantitative ticket questions → SQL query service.
    - "hybrid": Documentation/how-to questions → hybrid search (keyword + vector).
    - "clarify": Ambiguous queries → ask user for clarification.

    Classification parameters are set when corresponding route is set.
    """

    route: Literal["sql", "hybrid", "clarify"]
    confidence: float = Field(ge=0, le=1)
    sql_intent: SQLIntent | None = None
    document_query: str | None = None
    clarify_question: str | None = None


@dataclass
class WhereClause:
    """Result of building a dynamic WHERE clause for SQL queries.

    - sql - parameterized WHERE statement (e.g. "WHERE t.priority = :priority AND t.status = :status").
    - params - separate parameters of WHERE statement (e.g. {"priority": "p1", "status": "open"}).
    - needs_join - True when service_name filter is present in filter.
    """

    sql: str
    params: dict[str, Any]
    needs_join: bool


@dataclass
class DispatchResult:
    """Result of query returned by dispatch() using for building the answer prompt to user.

    - context - formatted text for LLM prompt.
    - sources - raw chunks for QuerySource (empty for sql/clarify).
    - route - "sql", "hybrid", or "clarify"

    Note: route reflects the actual handler used, which may differ from
    the originally classified route after fallback.
    """

    context: str
    sources: list[dict[str, Any]]
    route: str
