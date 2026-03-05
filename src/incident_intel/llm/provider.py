"""Chat provider protocol — defines the contract for LLM providers."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class ChatMessage:
    """Dataclass for a single message in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatProvider(Protocol):
    """Contract that chat provider must satisfy."""

    async def generate(self, messages: list[ChatMessage]) -> str:
        """Send a conversation to the provider and return the complete response as a string."""
        ...

    async def generate_stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Send a conversation to the provider and yield the response piece by piece as strings."""
        ...
