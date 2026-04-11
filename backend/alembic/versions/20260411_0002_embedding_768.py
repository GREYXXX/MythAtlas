"""change embedding vector dimension from 1536 to 768

Supports both local Ollama (nomic-embed-text, 768-dim) and OpenAI
text-embedding-3-small with dimensions=768 — both providers now use
the same dimension so embeddings are comparable.

Revision ID: 0002_embedding_768
Revises: 0001_initial
Create Date: 2026-04-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002_embedding_768"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector does not support ALTER COLUMN for dimension changes;
    # drop and recreate is the only path. Embeddings are nullable and
    # can be regenerated, so no data is lost.
    op.drop_column("stories", "embedding")
    op.add_column("stories", sa.Column("embedding", Vector(768), nullable=True))


def downgrade() -> None:
    op.drop_column("stories", "embedding")
    op.add_column("stories", sa.Column("embedding", Vector(1536), nullable=True))
