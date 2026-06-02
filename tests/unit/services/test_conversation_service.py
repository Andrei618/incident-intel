"""Unit tests for conversation service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from incident_intel.exceptions import ConversationNotFoundError
from incident_intel.models.conversation import Conversation
from incident_intel.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
)


async def test_get_conversation_returns_conversation() -> None:
    """Test get_conversation returns conversation object."""
    # Arrange
    test_conversation_id = uuid.uuid4()
    test_session = AsyncMock()
    test_session.scalar.return_value = Conversation(id=test_conversation_id)

    # Act
    result = await get_conversation(
        session=test_session,
        conversation_id=test_conversation_id,
    )

    # Assert
    assert result.id == test_conversation_id


async def test_get_conversation_raises_when_not_found() -> None:
    """Test get_conversation ConversationNotFoundError with non-existing  conversation_id."""
    # Arrange
    test_conversation_id = uuid.uuid4()
    test_session = AsyncMock()
    test_session.scalar.return_value = None

    # Act
    with pytest.raises(ConversationNotFoundError) as e:
        await get_conversation(
            session=test_session,
            conversation_id=test_conversation_id,
        )

    # Assert
    assert f"Conversation {test_conversation_id} not found" in str(e.value)


async def test_delete_conversation_calls_delete_and_commit() -> None:
    """Test delete_conversation call delete and commit."""
    # Arrange
    test_conversation_id = uuid.uuid4()
    test_session = AsyncMock()
    test_conversation = Conversation(id=test_conversation_id)
    test_session.scalar.return_value = test_conversation

    # Act
    await delete_conversation(
        session=test_session,
        conversation_id=test_conversation_id,
    )

    # Assert
    test_session.delete.assert_called_once_with(test_conversation)
    test_session.commit.assert_called_once()


async def test_delete_conversation_raises_when_not_found() -> None:
    """Test delete_conversation raises ConversationNotFoundError with non-existing  conversation_id."""
    # Arrange
    test_conversation_id = uuid.uuid4()
    test_session = AsyncMock()
    test_session.scalar.return_value = None

    # Act
    with pytest.raises(ConversationNotFoundError) as e:
        await delete_conversation(
            session=test_session,
            conversation_id=test_conversation_id,
        )

    # Assert
    assert f"Conversation {test_conversation_id} not found" in str(e.value)


async def test_list_conversations_returns_empty_list() -> None:
    """Test list_conversations returns empty list if no conversations stored."""
    # Arrange
    test_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    test_session.execute.return_value = mock_execute_result

    # Act
    result = await list_conversations(session=test_session)

    # Assert
    assert result == ([], 0)
