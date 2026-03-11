"""Controller flow accounting closure

Revision ID: 0013_flow_accounting
Revises: 0012_m6_rejected_sync
Create Date: 2026-03-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_flow_accounting"
down_revision: Union[str, None] = "0012_m6_rejected_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "non_sale_flows",
        sa.Column("non_sale_flow_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("tap_id", sa.Integer(), nullable=False),
        sa.Column("keg_id", sa.UUID(), nullable=True),
        sa.Column("volume_ml", sa.Integer(), nullable=False),
        sa.Column("accounted_volume_ml", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("flow_category", sa.String(length=64), nullable=False),
        sa.Column("session_state", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("card_present", sa.Boolean(), nullable=False),
        sa.Column("valve_open", sa.Boolean(), nullable=False),
        sa.Column("card_uid", sa.String(length=50), nullable=True),
        sa.Column("short_id", sa.String(length=8), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("volume_ml >= 0", name="ck_non_sale_flows_volume_non_negative"),
        sa.CheckConstraint(
            "accounted_volume_ml >= 0",
            name="ck_non_sale_flows_accounted_volume_non_negative",
        ),
        sa.ForeignKeyConstraint(["keg_id"], ["kegs.keg_id"]),
        sa.ForeignKeyConstraint(["tap_id"], ["taps.tap_id"]),
        sa.PrimaryKeyConstraint("non_sale_flow_id"),
    )
    op.create_index(op.f("ix_non_sale_flows_event_id"), "non_sale_flows", ["event_id"], unique=True)
    op.create_index(op.f("ix_non_sale_flows_tap_id"), "non_sale_flows", ["tap_id"], unique=False)
    op.create_index(op.f("ix_non_sale_flows_keg_id"), "non_sale_flows", ["keg_id"], unique=False)
    op.create_index(op.f("ix_non_sale_flows_flow_category"), "non_sale_flows", ["flow_category"], unique=False)
    op.create_index(op.f("ix_non_sale_flows_card_uid"), "non_sale_flows", ["card_uid"], unique=False)
    op.create_index(op.f("ix_non_sale_flows_short_id"), "non_sale_flows", ["short_id"], unique=False)
    op.create_index(op.f("ix_non_sale_flows_last_seen_at"), "non_sale_flows", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_non_sale_flows_finalized_at"), "non_sale_flows", ["finalized_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_non_sale_flows_finalized_at"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_last_seen_at"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_short_id"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_card_uid"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_flow_category"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_keg_id"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_tap_id"), table_name="non_sale_flows")
    op.drop_index(op.f("ix_non_sale_flows_event_id"), table_name="non_sale_flows")
    op.drop_table("non_sale_flows")
