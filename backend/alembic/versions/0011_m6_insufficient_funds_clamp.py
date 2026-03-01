"""M6 insufficient funds clamp defaults

Revision ID: 0011_m6_insufficient_funds_clamp
Revises: 0010_m5_db_time_source
Create Date: 2026-02-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_m6_insufficient_funds_clamp"
down_revision: Union[str, None] = "0010_m5_db_time_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SYSTEM_STATES = {
    "min_start_ml": "20",
    "safety_ml": "2",
    "allowed_overdraft_cents": "0",
}


def upgrade() -> None:
    bind = op.get_bind()
    states_table = sa.table(
        "system_states",
        sa.column("key", sa.String(length=50)),
        sa.column("value", sa.String(length=255)),
    )

    existing = {
        row[0]
        for row in bind.execute(sa.text("SELECT key FROM system_states"))
    }
    for key, value in DEFAULT_SYSTEM_STATES.items():
        if key in existing:
            continue
        bind.execute(states_table.insert().values(key=key, value=value))


def downgrade() -> None:
    # Defaults are additive runtime configuration and should not be deleted automatically.
    pass
