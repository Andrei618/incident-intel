"""Unit tests for classification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
from pydantic import ValidationError

from incident_intel.models.ticket import TicketPriority, TicketStatus
from incident_intel.schemas.classification import (
    QueryIntent,
    SqlAction,
    SQLIntent,
    TicketFilters,
)
from incident_intel.services.classification_service import classify_query


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_sql_count_query_classified_correctly(mock_client) -> None:
    """Test classify_query returns route=sql and sql_intent with filters with sql intention in query."""
    # Arrange
    query_intent_test = QueryIntent(
        route="sql",
        confidence=0.9,
        sql_intent=SQLIntent(
            action=SqlAction.COUNT,
            filters=TicketFilters(priority=TicketPriority.P1, status=TicketStatus.OPEN),
        ),
    )

    mock_message = MagicMock(parsed=query_intent_test, refusal=None)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "sql"
    assert result.confidence == 0.9
    assert result.sql_intent.action == "count"
    assert result.sql_intent.filters.priority == "p1"
    assert result.sql_intent.filters.status == "open"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_document_query_classified_as_hybrid(mock_client) -> None:
    """Test classify_query returns route=hybrid and document query set with document intention in query."""
    # Arrange
    query_intent_test = QueryIntent(
        route="hybrid",
        confidence=0.85,
        document_query="restart auth service",
    )

    mock_message = MagicMock(parsed=query_intent_test, refusal=None)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.85
    assert result.document_query == "restart auth service"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_ambiguous_query_classified_as_clarify(mock_client) -> None:
    """Test classify_query returns route=clarify and clarify question with ambiguous query."""
    # Arrange
    query_intent_test = QueryIntent(
        route="clarify",
        confidence=0.7,
        clarify_question="Could you be more specific?",
    )

    mock_message = MagicMock(parsed=query_intent_test, refusal=None)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "clarify"
    assert result.confidence == 0.7
    assert result.clarify_question == "Could you be more specific?"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_low_confidence_sql_falls_back_to_hybrid(mock_client) -> None:
    """Test classify_query overridden to hybrid when confidence < 0.6 + route=sql."""
    # Arrange
    query_intent_test = QueryIntent(
        route="sql",
        confidence=0.5,
        sql_intent=SQLIntent(action=SqlAction.COUNT),
    )

    mock_message = MagicMock(parsed=query_intent_test, refusal=None)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.5
    assert result.document_query == "test user question"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_low_confidence_clarify_stays_clarify(mock_client) -> None:
    """Test classify_query not overridden to hybrid when confidence < 0.6 + route=clarify."""
    # Arrange
    query_intent_test = QueryIntent(
        route="clarify",
        confidence=0.5,
        clarify_question="Could you be more specific?",
    )

    mock_message = MagicMock(parsed=query_intent_test, refusal=None)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "clarify"
    assert result.confidence == 0.5
    assert result.clarify_question == "Could you be more specific?"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_openai_api_error_falls_back_to_hybrid(mock_client) -> None:
    """Test classify_query overridden to hybrid + confidence=0.0 after API failure."""
    mock_client.chat.completions.parse.side_effect = openai.OpenAIError()

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.0


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_content_filter_length_error_falls_back_to_hybrid(mock_client) -> None:
    """Test classify_query overridden to hybrid after non-APIError OpenAI parse exception.

    Test any openai.OpenAIError subclass like ContentFilterFinishReasonError or LengthFinishReasonError.
    """
    # Arrange
    mock_client.chat.completions.parse.side_effect = openai.APIStatusError(
        message="content filtered",
        response=httpx.Response(
            status_code=400,
            request=httpx.Request(
                "POST", "https://api.openai.com"
            ),  # URL doesn't matter, it just needs to exist.
        ),
        body=None,
    )

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.0
    assert result.document_query == "test user question"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_validation_error_falls_back_to_hybrid(mock_client) -> None:
    """Test classify_query overridden to hybrid with invalid LLM values (e.g. bad datetime)."""
    # Arrange
    mock_client.chat.completions.parse.side_effect = ValidationError.from_exception_data(
        title="QueryIntent",
        line_errors=[],
        input_type="json",
    )

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.0
    assert result.document_query == "test user question"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_refusal_falls_back_to_hybrid(mock_client) -> None:
    """Test classify_query overridden to hybrid with ".refusal" in OpenAOI response."""
    # Arrange
    query_intent_test = QueryIntent(
        route="hybrid",
        confidence=0.85,
        document_query="restart auth service",
    )

    mock_message = MagicMock(parsed=query_intent_test, refusal="Refusal")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.0
    assert result.document_query == "test user question"


@patch("incident_intel.services.classification_service.client", new_callable=AsyncMock)
async def test_classify_query_parsed_is_none_falls_back_to_hybrid(mock_client) -> None:
    """Test classify_query overridden to hybrid with ".parsed" is None in OpenAOI response."""
    # Arrange
    mock_message = MagicMock(parsed=None, refusal=None)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.parse.return_value = mock_response

    # Act
    result = await classify_query(query="test user question")

    # Assert
    assert result.route == "hybrid"
    assert result.confidence == 0.0
    assert result.document_query == "test user question"
