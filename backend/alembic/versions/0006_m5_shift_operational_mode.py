"""M5 shift operational mode

Revision ID: 0006_m5_shift_operational_mode
Revises: 0005_m4_system_states_guard
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_m5_shift_operational_mode"
down_revision = "0005_m4_system_states_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shifts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("opened_by", sa.String(length=100), nullable=True),
        sa.Column("closed_by", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_shifts_status_values"),
    )
    op.create_index("ix_shifts_status", "shifts", ["status"], unique=False)
    op.create_index(
        "uq_shifts_one_open",
        "shifts",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("uq_shifts_one_open", table_name="shifts")
    op.drop_index("ix_shifts_status", table_name="shifts")
    op.drop_table("shifts")
