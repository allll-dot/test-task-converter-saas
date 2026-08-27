"""Add pgvector-backed transcript chunks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260827_03"
down_revision: str | None = "20260827_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "transcript_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transcript_chunks_organization_id"),
        "transcript_chunks",
        ["organization_id"],
    )
    op.create_index(op.f("ix_transcript_chunks_call_id"), "transcript_chunks", ["call_id"])
    if connection.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_transcript_chunks_embedding_hnsw "
            "ON transcript_chunks USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_transcript_chunks_call_id"), table_name="transcript_chunks")
    op.drop_index(op.f("ix_transcript_chunks_organization_id"), table_name="transcript_chunks")
    op.drop_table("transcript_chunks")
