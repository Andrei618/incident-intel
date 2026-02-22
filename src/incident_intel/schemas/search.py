"""Pydantic schema for search in documents."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SearchResultItem(BaseModel):
    """Response schema for detailed representation of one matching chunk.

    Includes chunk_id, document_id, document_title, content, chunk_index, score.
    """

    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    chunk_index: int
    score: float

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Response schema for top-level representation of chunk list.

    Includes items, query, total.
    """

    items: list[SearchResultItem]
    query: str
    total: int
