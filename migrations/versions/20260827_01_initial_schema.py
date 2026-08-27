"""Create organizations, calls and derived call analytics tables."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("audio_path", sa.String(length=1000), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="callstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_calls_organization_id"), "calls", ["organization_id"])
    op.create_index(op.f("ix_calls_status"), "calls", ["status"])
    op.create_table(
        "call_analyses",
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=300), nullable=False),
        sa.Column("result", sa.String(length=50), nullable=False),
        sa.Column("sentiment", sa.String(length=50), nullable=False),
        sa.Column("objections", sa.JSON(), nullable=False),
        sa.Column("agreements", sa.JSON(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.PrimaryKeyConstraint("call_id"),
    )
    op.create_index(op.f("ix_call_analyses_organization_id"), "call_analyses", ["organization_id"])
    op.create_table(
        "call_metrics",
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("manager_speech_seconds", sa.Float(), nullable=False),
        sa.Column("customer_speech_seconds", sa.Float(), nullable=False),
        sa.Column("unknown_speech_seconds", sa.Float(), nullable=False),
        sa.Column("manager_talk_ratio", sa.Float(), nullable=True),
        sa.Column("total_segments", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.PrimaryKeyConstraint("call_id"),
    )
    op.create_index(op.f("ix_call_metrics_organization_id"), "call_metrics", ["organization_id"])
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column(
            "speaker",
            sa.Enum("MANAGER", "CUSTOMER", "UNKNOWN", name="speaker", native_enum=False),
            nullable=False,
        ),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transcript_segments_call_id"), "transcript_segments", ["call_id"])
    op.create_index(
        op.f("ix_transcript_segments_organization_id"), "transcript_segments", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transcript_segments_organization_id"), table_name="transcript_segments")
    op.drop_index(op.f("ix_transcript_segments_call_id"), table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_index(op.f("ix_call_metrics_organization_id"), table_name="call_metrics")
    op.drop_table("call_metrics")
    op.drop_index(op.f("ix_call_analyses_organization_id"), table_name="call_analyses")
    op.drop_table("call_analyses")
    op.drop_index(op.f("ix_calls_status"), table_name="calls")
    op.drop_index(op.f("ix_calls_organization_id"), table_name="calls")
    op.drop_table("calls")
    op.drop_table("organizations")
