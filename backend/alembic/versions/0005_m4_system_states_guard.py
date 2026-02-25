"""M4 additive guard for system_states table

Revision ID: 0005_m4_system_states_guard
Revises: 0004_m4_offline_sync_reconcile
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_m4_system_states_guard"
down_revision = "0004_m4_offline_sync_reconcile"
branch_labels = None
depends_on = None


DEFAULT_SYSTEM_STATES = {
    "emergency_stop_enabled": "false",
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "system_states" not in inspector.get_table_names():
        op.create_table(
            "system_states",
            sa.Column("key", sa.String(length=50), nullable=False),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("key"),
        )
        op.create_index("ix_system_states_key", "system_states", ["key"], unique=False)

    states_table = sa.table(
        "system_states",
        sa.column("key", sa.String(length=50)),
        sa.column("value", sa.String(length=255)),
    )

    for key, value in DEFAULT_SYSTEM_STATES.items():
        stmt = (
            postgresql.insert(states_table)
            .values(key=key, value=value)
            .on_conflict_do_nothing(index_elements=["key"])
        )
        op.execute(stmt)


def downgrade() -> None:
    # This migration is an additive resilience guard; no destructive downgrade actions.
    pass
