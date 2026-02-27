"""M5 DB time source hardening for core timestamps

Revision ID: 0008_m5_db_time_source
Revises: 0007_m5_shift_reports_v1
Create Date: 2026-02-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_m5_db_time_source"
down_revision: Union[str, None] = "0007_m5_shift_reports_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now_sql() -> str:
    dialect = op.get_bind().dialect.name
    return "now()" if dialect == "postgresql" else "CURRENT_TIMESTAMP"


def upgrade() -> None:
    now_sql = _now_sql()

    # Backfill nullable legacy rows before NOT NULL constraints.
    op.execute(sa.text(f"UPDATE guests SET created_at = {now_sql} WHERE created_at IS NULL"))
    op.execute(sa.text(f"UPDATE guests SET updated_at = {now_sql} WHERE updated_at IS NULL"))
    op.execute(sa.text(f"UPDATE shifts SET opened_at = {now_sql} WHERE opened_at IS NULL"))
    op.execute(sa.text(f"UPDATE visits SET opened_at = {now_sql} WHERE opened_at IS NULL"))
    op.execute(sa.text(f"UPDATE transactions SET created_at = {now_sql} WHERE created_at IS NULL"))
    op.execute(sa.text(f"UPDATE audit_logs SET timestamp = {now_sql} WHERE timestamp IS NULL"))

    op.alter_column(
        "guests",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=False,
    )
    op.alter_column(
        "guests",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=False,
    )

    op.alter_column(
        "shifts",
        "opened_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=False,
    )

    op.alter_column(
        "visits",
        "opened_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=False,
    )

    op.alter_column(
        "transactions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=False,
    )

    op.alter_column(
        "audit_logs",
        "timestamp",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=False,
    )


def downgrade() -> None:
    now_sql = _now_sql()

    op.alter_column(
        "audit_logs",
        "timestamp",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=True,
    )

    op.alter_column(
        "transactions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=True,
    )

    op.alter_column(
        "guests",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=True,
    )
    op.alter_column(
        "guests",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text(now_sql),
        nullable=True,
    )
