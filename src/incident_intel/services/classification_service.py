"""Intent extraction service.

Classifies user queries and extracts parameters using OpenAI structured output.
Returns a QueryIntent with route, confidence, and route-specific data.
"""

import os
import time
from datetime import UTC, datetime

import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import ValidationError

from incident_intel.core.logging import get_logger
from incident_intel.schemas.classification import QueryIntent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-set")
OPENAI_MODEL_CLASSIFICATION = os.getenv("OPENAI_MODEL_CLASSIFICATION", "gpt-4o-mini")
TEMPERATURE = 0.0

CONFIDENCE_THRESHOLD = 0.6


client = openai.AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=30.0,
    max_retries=2,
)

logger = get_logger(__name__)


def _build_system_prompt() -> str:
    """Build system prompt for LLM with key rules to follow."""
    return f"""\
You are experienced system support engineer.
You have to choose which of these three routes should each user query be sent:
   - `sql` — quantitative ticket questions (counts, lists with filters),
   - `hybrid` — documentation, how-to, troubleshooting questions,
   - `clarify` — ambiguous or too vague to classify.
Today's date is {datetime.now(UTC).strftime("%Y-%m-%d")}.
Return all datetimes in UTC ISO format (e.g., 2026-03-02T00:00:00Z).
All date filters apply to ticket creation date only.
'limit' must be between 1 and 100.
For inclusive date ranges, use next-day midnight as the until value,
 for example 'March 3-7' → until: 2026-03-08T00:00:00Z.

Examples of classification:
   - "How many P1 tickets are open?" → `sql`, count, priority=p1, status=open
   - "List recent tickets for payment-service" → `sql`, list, service_name=payment-service
   - "How do I restart the auth service?" → `hybrid`, document_query="restart auth service"
   - "tickets" → `clarify`, clarify_question="Could you be more specific? I can help with ticket counts, lists, or search documentation."
"""


def _build_fallback_intent(query: str) -> QueryIntent:
    """Build a safe fallback intent when classification fails.

    Falls back to hybrid route to ensure that user still gets an answer.
    """
    return QueryIntent(
        route="hybrid",
        confidence=0.0,
        document_query=query,
    )


async def classify_query(query: str) -> QueryIntent:
    """Classify a user query into sql/hybrid/clarify route.

    Uses OpenAI structured output (response_format) to extract intent
    and parameters in a single LLM call. Returns fallback hybrid intent
    on any error.

    Args:
        query: The user's natural language question.

    Returns:
        QueryIntent with route, confidence, and route-specific data.
    """
    t_start = time.perf_counter()
    try:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": query},
        ]
        response = await client.chat.completions.parse(
            model=OPENAI_MODEL_CLASSIFICATION,
            messages=messages,
            response_format=QueryIntent,
            temperature=TEMPERATURE,
        )
        logger.info(
            "timing_classification",
            duration_ms=int((time.perf_counter() - t_start) * 1000),
            model=OPENAI_MODEL_CLASSIFICATION,
        )
        message = response.choices[0].message

        # Guard: refusal or empty/filtered content
        if message.refusal is not None or message.parsed is None:
            logger.info(
                "classification_refusal_or_empty_content",
                action="FALLBACK_TO_HYBRID",
            )
            return _build_fallback_intent(query)

        intent: QueryIntent = message.parsed

        # Confidence fallback — only override sql, not clarify
        if intent.confidence < CONFIDENCE_THRESHOLD and intent.route == "sql":
            intent.route = "hybrid"
            intent.document_query = intent.document_query or query
            logger.info(
                "classification_sql_threshold_hit",
                confidence=intent.confidence,
                action="FALLBACK_TO_HYBRID",
            )

        logger.info("classification_complete", route=intent.route, confidence=intent.confidence)
        return intent

    except (openai.OpenAIError, ValidationError) as e:
        logger.info(
            "timing_classification_failed", duration_ms=int((time.perf_counter() - t_start) * 1000)
        )
        logger.warning("classification_error", action="FALLBACK_TO_HYBRID")
        logger.debug("classification_error_detail", error=e)
        return _build_fallback_intent(query)
