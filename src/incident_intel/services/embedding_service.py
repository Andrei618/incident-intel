"""Service layer for embedding."""

import os

import openai
import tiktoken

from incident_intel.core.logging import get_logger

# Fallback allows module import in CI/tests where no API key is set.
# OpenAI client validates the key at request time, not at creation.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-set")

OPENAI_MODEL_EMBEDDING = os.getenv("OPENAI_MODEL_EMBEDDING", "text-embedding-3-small")
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


logger = get_logger(__name__)

encoding = tiktoken.encoding_for_model(OPENAI_MODEL_EMBEDDING)

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)


def chunk_text(
    content: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Chunk a document's content into overlapping pieces of text.

    Args:
        content: Text of the document to embed.
        chunk_size: Amount of tokens that is used to divide document to chunks.
        chunk_overlap: Amount of tokens that are shared between consecutive chunks.

    Returns:
        List of text units (chunks) of defined size.

    Example:
        >>> chunks = chunk_text(document.content)
    """
    tokens = encoding.encode(content)
    step = chunk_size - chunk_overlap
    chunks = []

    for start in range(0, len(tokens), step):
        token_chunk = tokens[start : start + chunk_size]
        chunks.append(encoding.decode(token_chunk))
    logger.info(
        "text_chunked", chunk_amount=len(chunks), chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return chunks


async def create_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via OpenAI API.

    Args:
        texts: List of strings to embed (document chunks or search queries)..

    Returns:
        List of embedding vectors (each vector is 1536 floats).

    Raises:
        openai.AuthenticationError: API key or token was invalid, expired, or revoked.
        openai.RateLimitError: Assigned rate limit was hit.
        openai.APITimeoutError: Request timed out.
        openai.BadRequestError: Request was malformed or missing some required parameters, such as a token or an input.

    Example:
        >>> embeddings = await create_embeddings(texts)
    """
    logger.info("chunks_embedding_started", text_count=len(texts))
    response = await client.embeddings.create(
        input=texts,
        model=OPENAI_MODEL_EMBEDDING,
    )
    embeddings = [item.embedding for item in response.data]
    logger.info("chunks_embedding_finished", embedding_count=len(embeddings))
    logger.debug(
        "chunks_embedding_finished_detail",
        embedding_count=len(embeddings),
        first_embedding=embeddings[0][:5] if embeddings else None,
    )
    return embeddings
