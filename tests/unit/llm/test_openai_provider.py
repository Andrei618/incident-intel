"""Unit tests for OpenAI chat completion provider."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from incident_intel.llm.openai_provider import OpenAIChatProvider, _to_openai_message
from incident_intel.llm.provider import ChatMessage


def test_to_openai_message_user_role_returns_correct_dict() -> None:
    """Test _to_openai_message user role returns correct dict."""
    # Arrange
    message = ChatMessage(role="user", content="test content")

    # Act
    messages_openai = _to_openai_message(message)

    # Assert
    assert messages_openai["role"] == "user"
    assert messages_openai["content"] == "test content"


def test_to_openai_message_system_role_returns_correct_dict() -> None:
    """Test _to_openai_message system role returns correct dict."""
    # Arrange
    message = ChatMessage(role="system", content="test content")

    # Act
    messages_openai = _to_openai_message(message)

    # Assert
    assert messages_openai["role"] == "system"
    assert messages_openai["content"] == "test content"


def test_to_openai_message_assistant_role_returns_correct_dict() -> None:
    """Test _to_openai_message assistant role returns correct dict."""
    # Arrange
    message = ChatMessage(role="assistant", content="test content")

    # Act
    messages_openai = _to_openai_message(message)

    # Assert
    assert messages_openai["role"] == "assistant"
    assert messages_openai["content"] == "test content"


def test_to_openai_message_unknown_role_raises_value_error() -> None:
    """Test _to_openai_message unknown role raises ValueError."""
    # Arrange
    message = ChatMessage(role="unknown", content="test content")

    # Act
    with pytest.raises(ValueError) as e:
        _to_openai_message(message)

    # Assert
    assert "Unknown role" in str(e.value)


@patch("incident_intel.llm.openai_provider.client", new_callable=AsyncMock)
async def test_generate_returns_text_with_correct_params(mock_client) -> None:
    """Test generate returns text and verify API called with correct params."""
    # Arrange
    message_1 = ChatMessage(role="user", content="test content 1")
    message_2 = ChatMessage(role="user", content="test content 2")
    messages = [message_1, message_2]

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "test response"

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAIChatProvider()

    # Act
    response_text = await provider.generate(messages)

    # Assert
    assert "test response" in response_text
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "test content 1"},
            {"role": "user", "content": "test content 2"},
        ],
        temperature=0.2,
    )


@patch("incident_intel.llm.openai_provider.client", new_callable=AsyncMock)
async def test_generate_returns_text_with_non_default_model_and_temperature(mock_client) -> None:
    """Test generate returns text with non-default values for model and temperature."""
    # Arrange
    message_1 = ChatMessage(role="user", content="test content 1")
    message_2 = ChatMessage(role="user", content="test content 2")
    messages = [message_1, message_2]

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "test response"

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAIChatProvider(model="gpt-4o", temperature=0.5)

    # Act
    response_text = await provider.generate(messages)

    # Assert
    assert "test response" in response_text
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "test content 1"},
            {"role": "user", "content": "test content 2"},
        ],
        temperature=0.5,
    )


@patch("incident_intel.llm.openai_provider.client", new_callable=AsyncMock)
async def test_generate_none_content_returns_empty_string(mock_client) -> None:
    """Test generate returns "" when the API response has content = None."""
    # Arrange
    message_1 = ChatMessage(role="user", content="test content 1")
    message_2 = ChatMessage(role="user", content="test content 2")
    messages = [message_1, message_2]

    mock_response = MagicMock()
    mock_response.choices[0].message.content = None

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAIChatProvider()

    # Act
    response_text = await provider.generate(messages)

    # Assert
    assert response_text == ""


@patch("incident_intel.llm.openai_provider.client", new_callable=AsyncMock)
async def test_generate_stream_yields_chunks_skips_none(mock_client) -> None:
    """Test generate_stream yields chunks and skips None."""

    # Arrange
    async def mock_stream() -> AsyncIterator[MagicMock]:
        """Yield mock chunks like OpenAI's streaming response."""
        for content in ["Hello", None, " world"]:
            chunk = MagicMock()
            chunk.choices[0].delta.content = content
            yield chunk

    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    message_1 = ChatMessage(role="user", content="test content 1")
    message_2 = ChatMessage(role="user", content="test content 2")
    messages = [message_1, message_2]

    provider = OpenAIChatProvider()
    # Act
    result = [chunk async for chunk in provider.generate_stream(messages)]

    # Assert
    assert result == ["Hello", " world"]  # None was skipped!
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "test content 1"},
            {"role": "user", "content": "test content 2"},
        ],
        temperature=0.2,
        stream=True,
    )
