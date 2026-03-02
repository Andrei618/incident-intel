"""Add content_tsv generated column to document_chunks.

Revision ID: 60c303fdc3e3
Revises: 893e862bb9cb
Create Date: 2026-02-22 13:33:12.663466

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "60c303fdc3e3"
down_revision: str | Sequence[str] | None = "893e862bb9cb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade: add content_tsv column to document_chunks and index on it."""
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS content_tsv tsvector"
        " GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_tsv"
        " ON document_chunks USING GIN (content_tsv)"
    )


def downgrade() -> None:
    """Downgrade: drop content_tsv column in document_chunks and index on it."""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv")
