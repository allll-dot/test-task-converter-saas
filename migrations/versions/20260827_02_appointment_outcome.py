"""Add appointment outcome to call analysis."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_02"
down_revision: str | None = "20260827_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "call_analyses",
        sa.Column(
            "appointment_status",
            sa.Enum(
                "BOOKED",
                "NOT_BOOKED",
                "RESCHEDULED",
                "CANCELLED",
                "NOT_APPLICABLE",
                "UNKNOWN",
                name="appointmentstatus",
                native_enum=False,
            ),
            server_default="UNKNOWN",
            nullable=False,
        ),
    )
    op.add_column(
        "call_analyses",
        sa.Column("appointment_datetime", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "call_analyses",
        sa.Column("appointment_service", sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call_analyses", "appointment_service")
    op.drop_column("call_analyses", "appointment_datetime")
    op.drop_column("call_analyses", "appointment_status")
