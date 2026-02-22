"""M3.5 open visit without card

Revision ID: 0003_m35_open_visit_without_card
Revises: 0002_m2_visit_model
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_m35_open_visit_without_card"
down_revision = "0002_m2_visit_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("visits", "card_uid", existing_type=sa.String(length=50), nullable=True)

    op.drop_index("uq_visits_one_active_per_card", table_name="visits")
    op.create_index(
        "uq_visits_one_active_per_card",
        "visits",
        ["card_uid"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND card_uid IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_visits_one_active_per_card", table_name="visits")
    op.create_index(
        "uq_visits_one_active_per_card",
        "visits",
        ["card_uid"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.alter_column("visits", "card_uid", existing_type=sa.String(length=50), nullable=False)
