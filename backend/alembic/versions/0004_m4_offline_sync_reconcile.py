"""M4 offline sync + manual reconcile

Revision ID: 0004_m4_offline_sync_reconcile
Revises: 0003_m35_open_visit_without_card
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_m4_offline_sync_reconcile"
down_revision = "0003_m35_open_visit_without_card"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pours",
        sa.Column("sync_status", sa.String(length=20), nullable=False, server_default=sa.text("'synced'")),
    )
    op.add_column("pours", sa.Column("short_id", sa.String(length=8), nullable=True))
    op.add_column(
        "pours",
        sa.Column("is_manual_reconcile", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_pours_sync_status", "pours", ["sync_status"], unique=False)
    op.create_index("ix_pours_short_id", "pours", ["short_id"], unique=False)
    op.create_index(
        "uq_pours_visit_short_id",
        "pours",
        ["visit_id", "short_id"],
        unique=True,
        postgresql_where=sa.text("short_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_pours_sync_status_values",
        "pours",
        "sync_status IN ('pending_sync', 'synced', 'reconciled')",
    )

    op.add_column("visits", sa.Column("lock_set_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_visits_lock_set_at", "visits", ["lock_set_at"], unique=False)

    op.alter_column("pours", "sync_status", server_default=None)
    op.alter_column("pours", "is_manual_reconcile", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_visits_lock_set_at", table_name="visits")
    op.drop_column("visits", "lock_set_at")

    op.drop_constraint("ck_pours_sync_status_values", "pours", type_="check")
    op.drop_index("uq_pours_visit_short_id", table_name="pours")
    op.drop_index("ix_pours_short_id", table_name="pours")
    op.drop_index("ix_pours_sync_status", table_name="pours")
    op.drop_column("pours", "is_manual_reconcile")
    op.drop_column("pours", "short_id")
    op.drop_column("pours", "sync_status")
