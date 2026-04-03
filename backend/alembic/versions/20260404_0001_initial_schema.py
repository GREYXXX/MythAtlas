"""initial schema: stories with postgis and pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from pgvector.sqlalchemy import Vector

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "stories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title_en", sa.String(length=512), nullable=False),
        sa.Column("title_zh", sa.String(length=512), nullable=False),
        sa.Column("content_en", sa.Text(), nullable=False),
        sa.Column("content_zh", sa.Text(), nullable=False),
        sa.Column("country", sa.String(length=128), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.String(length=128)), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stories_country"), "stories", ["country"], unique=False)
    op.execute("CREATE INDEX IF NOT EXISTS ix_stories_location_gist ON stories USING GIST (location)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stories_location_gist")
    op.drop_index(op.f("ix_stories_country"), table_name="stories")
    op.drop_table("stories")
