"""M5 shift reports v1

Revision ID: 0007_m5_shift_reports_v1
Revises: 0006_m5_shift_operational_mode
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_m5_shift_reports_v1"
down_revision = "0006_m5_shift_operational_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shift_reports",
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("shift_id", sa.UUID(), nullable=False),
        sa.Column("report_type", sa.String(length=1), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("report_type IN ('X', 'Z')", name="ck_shift_reports_report_type_values"),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("report_id"),
    )

    op.create_index("idx_shift_reports_shift_id", "shift_reports", ["shift_id"], unique=False)
    op.create_index("idx_shift_reports_generated_at", "shift_reports", ["generated_at"], unique=False)
    op.create_index(
        "uq_shift_reports_one_z_per_shift",
        "shift_reports",
        ["shift_id"],
        unique=True,
        postgresql_where=sa.text("report_type = 'Z'"),
    )


def downgrade() -> None:
    op.drop_index("uq_shift_reports_one_z_per_shift", table_name="shift_reports")
    op.drop_index("idx_shift_reports_generated_at", table_name="shift_reports")
    op.drop_index("idx_shift_reports_shift_id", table_name="shift_reports")
    op.drop_table("shift_reports")
