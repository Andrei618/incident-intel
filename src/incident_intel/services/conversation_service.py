"""Service layer for conversation operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.exceptions import ConversationNotFoundError
from incident_intel.models.conversation import Conversation

logger = get_logger(__name__)


async def get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> Conversation:
    """Get a conversation by ID.

    Args:
        session: active database session.
        conversation_id: UUID of conversation to retrieve.

    Returns:
        The requested conversation.

    Raises:
        ConversationNotFoundError: If conversation does not exist.
    """
    logger.debug("fetching_conversation", conversation_id=str(conversation_id))

    stmt = select(Conversation).where(Conversation.id == conversation_id)
    conversation = await session.scalar(stmt)

    if conversation is None:
        logger.warning("conversation_not_found", conversation_id=str(conversation_id))
        raise ConversationNotFoundError(conversation_id)

    logger.debug("conversation_found", conversation_id=str(conversation_id))
    return conversation


async def delete_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> None:
    """Delete conversation by ID.

    Args:
        session: active database session.
        conversation_id: UUID of conversation to delete.

    Raises:
        ConversationNotFoundError: If conversation does not exist.
    """
    logger.info("deleting_conversation", conversation_id=str(conversation_id))

    conversation = await get_conversation(session, conversation_id)

    await session.delete(conversation)
    await session.commit()

    logger.info("conversation_deleted", conversation_id=str(conversation_id))


async def list_conversations(
    session: AsyncSession,
) -> tuple[list[Conversation], int]:
    """List conversations.

    Args:
        session: active database session.

    Returns:
        Tuple: list of conversations, total count of conversations.
    """
    stmt = select(Conversation).order_by(Conversation.created_at.desc())
    result = await session.execute(stmt)
    conversations = list(result.scalars().all())

    total = len(conversations)

    logger.debug("conversations_listed", count=total)

    return conversations, total
