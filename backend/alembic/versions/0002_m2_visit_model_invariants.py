"""M2 visit model + invariants

Revision ID: 0002_m2_visit_model
Revises: 0001_m1_baseline
Create Date: 2026-02-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_m2_visit_model"
down_revision = "0001_m1_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visits",
        sa.Column("visit_id", sa.UUID(), nullable=False),
        sa.Column("guest_id", sa.UUID(), nullable=False),
        sa.Column("card_uid", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        # M3 placeholder: intentionally no FK in M2.
        sa.Column("active_tap_id", sa.Integer(), nullable=True),
        sa.Column("card_returned", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["card_uid"], ["cards.card_uid"]),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.guest_id"]),
        sa.PrimaryKeyConstraint("visit_id"),
        sa.CheckConstraint(
            "(status <> 'closed') OR (closed_at IS NOT NULL)",
            name="ck_visits_closed_requires_closed_at",
        ),
    )

    op.create_index("ix_visits_guest_id", "visits", ["guest_id"], unique=False)
    op.create_index("ix_visits_card_uid", "visits", ["card_uid"], unique=False)
    op.create_index("ix_visits_status", "visits", ["status"], unique=False)
    op.create_index(
        "uq_visits_one_active_per_guest",
        "visits",
        ["guest_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_visits_one_active_per_card",
        "visits",
        ["card_uid"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.add_column("pours", sa.Column("visit_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_pours_visit_id_visits", "pours", "visits", ["visit_id"], ["visit_id"])
    op.create_index("ix_pours_visit_id", "pours", ["visit_id"], unique=False)

    op.add_column("transactions", sa.Column("visit_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_transactions_visit_id_visits", "transactions", "visits", ["visit_id"], ["visit_id"])
    op.create_index("ix_transactions_visit_id", "transactions", ["visit_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_visit_id", table_name="transactions")
    op.drop_constraint("fk_transactions_visit_id_visits", "transactions", type_="foreignkey")
    op.drop_column("transactions", "visit_id")

    op.drop_index("ix_pours_visit_id", table_name="pours")
    op.drop_constraint("fk_pours_visit_id_visits", "pours", type_="foreignkey")
    op.drop_column("pours", "visit_id")

    op.drop_index("uq_visits_one_active_per_card", table_name="visits")
    op.drop_index("uq_visits_one_active_per_guest", table_name="visits")
    op.drop_index("ix_visits_status", table_name="visits")
    op.drop_index("ix_visits_card_uid", table_name="visits")
    op.drop_index("ix_visits_guest_id", table_name="visits")
    op.drop_table("visits")
