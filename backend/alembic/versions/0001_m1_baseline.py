"""M1 baseline

Revision ID: 0001_m1_baseline
Revises:
Create Date: 2026-02-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_m1_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_entity", sa.String(), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)

    op.create_table(
        "beverages",
        sa.Column("beverage_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("brewery", sa.String(length=100), nullable=True),
        sa.Column("style", sa.String(length=50), nullable=True),
        sa.Column("abv", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("sell_price_per_liter", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.PrimaryKeyConstraint("beverage_id"),
    )
    op.create_index("ix_beverages_name", "beverages", ["name"], unique=True)

    op.create_table(
        "controllers",
        sa.Column("controller_id", sa.String(length=50), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("firmware_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("controller_id"),
    )
    op.create_index("ix_controllers_controller_id", "controllers", ["controller_id"], unique=False)

    op.create_table(
        "guests",
        sa.Column("guest_id", sa.UUID(), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("patronymic", sa.String(length=50), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("id_document", sa.String(length=100), nullable=False),
        sa.Column("balance", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("guest_id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index("ix_guests_id_document", "guests", ["id_document"], unique=False)
    op.create_index("ix_guests_last_name", "guests", ["last_name"], unique=False)

    op.create_table(
        "system_states",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_system_states_key", "system_states", ["key"], unique=False)

    op.create_table(
        "cards",
        sa.Column("card_uid", sa.String(length=50), nullable=False),
        sa.Column("guest_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.guest_id"]),
        sa.PrimaryKeyConstraint("card_uid"),
    )
    op.create_index("ix_cards_guest_id", "cards", ["guest_id"], unique=False)
    op.create_index("ix_cards_status", "cards", ["status"], unique=False)

    op.create_table(
        "kegs",
        sa.Column("keg_id", sa.UUID(), nullable=False),
        sa.Column("beverage_id", sa.UUID(), nullable=False),
        sa.Column("initial_volume_ml", sa.Integer(), nullable=False),
        sa.Column("current_volume_ml", sa.Integer(), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("tapped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["beverage_id"], ["beverages.beverage_id"]),
        sa.PrimaryKeyConstraint("keg_id"),
    )
    op.create_index("ix_kegs_beverage_id", "kegs", ["beverage_id"], unique=False)
    op.create_index("ix_kegs_status", "kegs", ["status"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("guest_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.guest_id"]),
        sa.PrimaryKeyConstraint("transaction_id"),
    )
    op.create_index("ix_transactions_guest_id", "transactions", ["guest_id"], unique=False)

    op.create_table(
        "taps",
        sa.Column("tap_id", sa.Integer(), nullable=False),
        sa.Column("keg_id", sa.UUID(), nullable=True),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_cleaned_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["keg_id"], ["kegs.keg_id"]),
        sa.PrimaryKeyConstraint("tap_id"),
        sa.UniqueConstraint("display_name"),
        sa.UniqueConstraint("keg_id"),
    )
    op.create_index("ix_taps_status", "taps", ["status"], unique=False)

    op.create_table(
        "pours",
        sa.Column("pour_id", sa.UUID(), nullable=False),
        sa.Column("client_tx_id", sa.String(length=100), nullable=False),
        sa.Column("guest_id", sa.UUID(), nullable=False),
        sa.Column("card_uid", sa.String(length=50), nullable=False),
        sa.Column("tap_id", sa.Integer(), nullable=False),
        sa.Column("keg_id", sa.UUID(), nullable=False),
        sa.Column("volume_ml", sa.Integer(), nullable=False),
        sa.Column("amount_charged", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("price_per_ml_at_pour", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("poured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["card_uid"], ["cards.card_uid"]),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.guest_id"]),
        sa.ForeignKeyConstraint(["keg_id"], ["kegs.keg_id"]),
        sa.ForeignKeyConstraint(["tap_id"], ["taps.tap_id"]),
        sa.PrimaryKeyConstraint("pour_id"),
    )
    op.create_index("ix_pours_card_uid", "pours", ["card_uid"], unique=False)
    op.create_index("ix_pours_client_tx_id", "pours", ["client_tx_id"], unique=True)
    op.create_index("ix_pours_guest_id", "pours", ["guest_id"], unique=False)
    op.create_index("ix_pours_keg_id", "pours", ["keg_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pours_keg_id", table_name="pours")
    op.drop_index("ix_pours_guest_id", table_name="pours")
    op.drop_index("ix_pours_client_tx_id", table_name="pours")
    op.drop_index("ix_pours_card_uid", table_name="pours")
    op.drop_table("pours")

    op.drop_index("ix_taps_status", table_name="taps")
    op.drop_table("taps")

    op.drop_index("ix_transactions_guest_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_kegs_status", table_name="kegs")
    op.drop_index("ix_kegs_beverage_id", table_name="kegs")
    op.drop_table("kegs")

    op.drop_index("ix_cards_status", table_name="cards")
    op.drop_index("ix_cards_guest_id", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ix_system_states_key", table_name="system_states")
    op.drop_table("system_states")

    op.drop_index("ix_guests_last_name", table_name="guests")
    op.drop_index("ix_guests_id_document", table_name="guests")
    op.drop_table("guests")

    op.drop_index("ix_controllers_controller_id", table_name="controllers")
    op.drop_table("controllers")

    op.drop_index("ix_beverages_name", table_name="beverages")
    op.drop_table("beverages")

    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
