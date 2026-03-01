"""M6 rejected pour terminal state

Revision ID: 0012_m6_rejected_sync
Revises: 0011_m6_insufficient_funds_clamp
Create Date: 2026-02-28
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0012_m6_rejected_sync"
down_revision: Union[str, None] = "0011_m6_insufficient_funds_clamp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_pours_sync_status_values", "pours", type_="check")
    op.create_check_constraint(
        "ck_pours_sync_status_values",
        "pours",
        "sync_status IN ('pending_sync', 'synced', 'reconciled', 'rejected')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pours_sync_status_values", "pours", type_="check")
    op.create_check_constraint(
        "ck_pours_sync_status_values",
        "pours",
        "sync_status IN ('pending_sync', 'synced', 'reconciled')",
    )
