"""guest visit card consolidation

Revision ID: 0016_guest_visit_card_consolidation
Revises: 0015_incident_state_overlay
Create Date: 2026-03-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_guest_visit_card_consolidation"
down_revision: Union[str, Sequence[str], None] = "0015_incident_state_overlay"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assert_no_case_duplicates(bind, table_name: str, column_name: str) -> None:
    duplicates = bind.execute(
        sa.text(
            f"""
            SELECT lower(trim({column_name})) AS normalized_uid, count(*) AS row_count
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
            GROUP BY lower(trim({column_name}))
            HAVING count(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        normalized_values = ", ".join(str(row[0]) for row in duplicates[:10])
        raise RuntimeError(
            f"Migration blocked: {table_name}.{column_name} contains case-only duplicates. "
            f"Resolve duplicates before applying 0016. Examples: {normalized_values}"
        )


def _assert_no_cardless_visits(bind) -> None:
    count = bind.execute(
        sa.text("SELECT count(*) FROM visits WHERE card_uid IS NULL OR trim(card_uid) = ''")
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Migration blocked: visits without card_uid still exist. "
            "Resolve legacy cardless visits before applying 0016."
        )


def upgrade() -> None:
    bind = op.get_bind()
    _assert_no_case_duplicates(bind, "cards", "card_uid")
    _assert_no_case_duplicates(bind, "lost_cards", "card_uid")
    _assert_no_cardless_visits(bind)

    op.add_column(
        "visits",
        sa.Column(
            "operational_status",
            sa.String(length=64),
            nullable=False,
            server_default="active_assigned",
        ),
    )
    op.add_column("visits", sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("visits", sa.Column("returned_by", sa.String(length=100), nullable=True))
    op.add_column("visits", sa.Column("return_method", sa.String(length=64), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE cards
            SET status = 'assigned_to_visit'
            WHERE EXISTS (
                SELECT 1
                FROM visits
                WHERE visits.status = 'active'
                  AND lower(trim(visits.card_uid)) = lower(trim(cards.card_uid))
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE cards
            SET status = 'lost'
            WHERE status = 'lost'
               OR EXISTS (
                    SELECT 1
                    FROM lost_cards
                    WHERE lower(trim(lost_cards.card_uid)) = lower(trim(cards.card_uid))
               )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE cards
            SET status = 'returned_to_pool'
            WHERE status IS NULL
               OR status IN ('inactive', 'active')
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE visits
            SET operational_status = CASE
                WHEN status = 'active' AND EXISTS (
                    SELECT 1
                    FROM lost_cards
                    WHERE lower(trim(lost_cards.card_uid)) = lower(trim(visits.card_uid))
                      AND (
                          lost_cards.visit_id = visits.visit_id
                          OR lost_cards.visit_id IS NULL
                      )
                ) THEN 'active_blocked_lost_card'
                WHEN status = 'active' THEN 'active_assigned'
                WHEN card_returned = 1 THEN 'closed_ok'
                ELSE 'closed_missing_card'
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE visits
            SET returned_at = closed_at
            WHERE card_returned = 1
              AND closed_at IS NOT NULL
              AND returned_at IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE visits
            SET return_method = 'legacy_backfill'
            WHERE card_returned = 1
              AND return_method IS NULL
            """
        )
    )

    with op.batch_alter_table("cards") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            existing_nullable=False,
            server_default="available",
        )

    with op.batch_alter_table("visits") as batch_op:
        batch_op.alter_column(
            "card_uid",
            existing_type=sa.String(length=50),
            nullable=False,
        )
        batch_op.alter_column(
            "operational_status",
            existing_type=sa.String(length=64),
            nullable=False,
            server_default="active_assigned",
        )


def downgrade() -> None:
    with op.batch_alter_table("visits") as batch_op:
        batch_op.alter_column(
            "card_uid",
            existing_type=sa.String(length=50),
            nullable=True,
        )
        batch_op.drop_column("return_method")
        batch_op.drop_column("returned_by")
        batch_op.drop_column("returned_at")
        batch_op.drop_column("operational_status")

    with op.batch_alter_table("cards") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            existing_nullable=False,
            server_default="inactive",
        )
