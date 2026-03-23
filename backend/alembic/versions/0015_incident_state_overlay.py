"""incident state overlay

Revision ID: 0015_incident_state_overlay
Revises: 0014_tap_display_system
Create Date: 2026-03-23 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015_incident_state_overlay"
down_revision: Union[str, Sequence[str], None] = "0014_tap_display_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_states",
        sa.Column("incident_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=True),
        sa.Column("last_action", sa.String(length=64), nullable=True),
        sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_note", sa.Text(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closure_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    op.create_index("ix_incident_states_status", "incident_states", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_incident_states_status", table_name="incident_states")
    op.drop_table("incident_states")
