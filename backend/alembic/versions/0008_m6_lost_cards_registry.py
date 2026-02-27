"""M6 simplified lost cards registry

Revision ID: 0008_m6_lost_cards_registry
Revises: 0007_m5_shift_reports_v1
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_m6_lost_cards_registry"
down_revision = "0007_m5_shift_reports_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lost_cards",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("card_uid", sa.String(length=50), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reported_by", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("visit_id", sa.UUID(), nullable=True),
        sa.Column("guest_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.guest_id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.visit_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_uid", name="uq_lost_cards_card_uid"),
    )

    op.create_index("ix_lost_cards_card_uid", "lost_cards", ["card_uid"], unique=False)
    op.create_index("ix_lost_cards_reported_at", "lost_cards", ["reported_at"], unique=False)
    op.create_index("ix_lost_cards_visit_id", "lost_cards", ["visit_id"], unique=False)
    op.create_index("ix_lost_cards_guest_id", "lost_cards", ["guest_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lost_cards_guest_id", table_name="lost_cards")
    op.drop_index("ix_lost_cards_visit_id", table_name="lost_cards")
    op.drop_index("ix_lost_cards_reported_at", table_name="lost_cards")
    op.drop_index("ix_lost_cards_card_uid", table_name="lost_cards")
    op.drop_table("lost_cards")
