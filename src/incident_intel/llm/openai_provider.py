"""OpenAI chat provider — concrete implementation of ChatProvider."""

import os
from collections.abc import AsyncIterator

import openai
from openai.types.chat import ChatCompletionMessageParam

from incident_intel.core.logging import get_logger
from incident_intel.llm.provider import ChatMessage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-set")
OPENAI_MODEL_CHAT = os.getenv("OPENAI_MODEL_CHAT", "gpt-4o-mini")
TEMPERATURE = 0.2

client = openai.AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=30.0,
    max_retries=2,
)

logger = get_logger(__name__)


def _to_openai_message(m: ChatMessage) -> ChatCompletionMessageParam:
    """Convert a ChatMessage to an OpenAI ChatCompletionMessageParam."""
    if m.role == "user":
        return {"role": "user", "content": m.content}
    if m.role == "system":
        return {"role": "system", "content": m.content}
    if m.role == "assistant":
        return {"role": "assistant", "content": m.content}
    raise ValueError(f"Unknown role: {m.role}")


class OpenAIChatProvider:
    """Concrete class of chat provider."""

    def __init__(self, model: str = OPENAI_MODEL_CHAT, temperature: float = TEMPERATURE) -> None:
        """Initialize instance attributes."""
        self.model = model
        self.temperature = temperature

    async def generate(self, messages: list[ChatMessage]) -> str:
        """Generate a chat completion via the OpenAI API.

        Args:
            messages: list of ChatMessage objects with two attributes: role and content.

        Returns:
            String - text response from chat completion.

        Raises:
            openai.AuthenticationError: API key or token was invalid, expired, or revoked.
            openai.RateLimitError: Assigned rate limit was hit.
            openai.APITimeoutError: Request timed out.
            openai.BadRequestError: Request was malformed or missing some required parameters, such as a token or an input.
        """
        messages_openai = [_to_openai_message(m) for m in messages]

        logger.info("openai_chat_started", messages_count=len(messages_openai))

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages_openai,
            temperature=self.temperature,
        )

        response_text = response.choices[0].message.content or ""  # OpenAI returns str | None

        logger.info("openai_chat_finished", response_length=len(response_text))
        logger.debug(
            "openai_chat_finished_detail",
            response_length=len(response_text),
            response_text=response_text[:20] if response_text else None,
        )
        return response_text

    async def generate_stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Generate a chat completion via the OpenAI API (in streaming mode).

        Args:
            messages: list of ChatMessage objects with two attributes: role and content.

        Returns:
            AsyncIterator - iterable object yielding the response piece by piece as strings from chat completion.

        Raises:
            openai.AuthenticationError: API key or token was invalid, expired, or revoked.
            openai.RateLimitError: Assigned rate limit was hit.
            openai.APITimeoutError: Request timed out.
            openai.BadRequestError: Request was malformed or missing some required parameters, such as a token or an input.
        """
        messages_openai = [_to_openai_message(m) for m in messages]

        logger.info("openai_chat_stream_started", messages_count=len(messages_openai))

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages_openai,
            temperature=self.temperature,
            stream=True,
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content is None:
                continue
            yield content
