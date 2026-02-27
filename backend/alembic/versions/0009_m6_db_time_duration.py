"""M6 DB-time duration contract for pours

Revision ID: 0009_m6_db_time_duration
Revises: 0008_m6_lost_cards_registry
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_m6_db_time_duration"
down_revision = "0008_m6_lost_cards_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pours", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("pours", sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pours", sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pours", sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("pours", "poured_at", server_default=sa.text("now()"))

    op.execute(
        """
        UPDATE pours
        SET authorized_at = COALESCE(authorized_at, poured_at, created_at, now())
        WHERE sync_status = 'pending_sync'
        """
    )
    op.execute(
        """
        UPDATE pours
        SET synced_at = COALESCE(synced_at, poured_at, created_at, now())
        WHERE sync_status = 'synced'
        """
    )
    op.execute(
        """
        UPDATE pours
        SET reconciled_at = COALESCE(reconciled_at, poured_at, created_at, now())
        WHERE sync_status = 'reconciled'
        """
    )


def downgrade() -> None:
    op.alter_column("pours", "poured_at", server_default=None)
    op.drop_column("pours", "reconciled_at")
    op.drop_column("pours", "synced_at")
    op.drop_column("pours", "authorized_at")
    op.drop_column("pours", "duration_ms")
