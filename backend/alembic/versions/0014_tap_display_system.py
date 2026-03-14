"""Tap display system foundation

Revision ID: 0014_tap_display_system
Revises: 0013_flow_accounting
Create Date: 2026-03-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_tap_display_system"
down_revision: Union[str, None] = "0013_flow_accounting"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("asset_id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_media_assets_kind"), "media_assets", ["kind"], unique=False)
    op.create_index(op.f("ix_media_assets_checksum_sha256"), "media_assets", ["checksum_sha256"], unique=False)

    with op.batch_alter_table("beverages") as batch_op:
        batch_op.add_column(sa.Column("description_short", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("ibu", sa.Numeric(5, 2), nullable=True))
        batch_op.add_column(sa.Column("display_brand_name", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("accent_color", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("background_asset_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("logo_asset_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("text_theme", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("price_display_mode_default", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch_op.create_foreign_key(
            "fk_beverages_background_asset_id_media_assets",
            "media_assets",
            ["background_asset_id"],
            ["asset_id"],
        )
        batch_op.create_foreign_key(
            "fk_beverages_logo_asset_id_media_assets",
            "media_assets",
            ["logo_asset_id"],
            ["asset_id"],
        )

    op.create_table(
        "tap_display_configs",
        sa.Column("tap_id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("idle_instruction", sa.Text(), nullable=True),
        sa.Column("fallback_title", sa.String(length=120), nullable=True),
        sa.Column("fallback_subtitle", sa.Text(), nullable=True),
        sa.Column("maintenance_title", sa.String(length=120), nullable=True),
        sa.Column("maintenance_subtitle", sa.Text(), nullable=True),
        sa.Column("override_accent_color", sa.String(length=32), nullable=True),
        sa.Column("override_background_asset_id", sa.UUID(), nullable=True),
        sa.Column("show_price_mode", sa.String(length=16), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["override_background_asset_id"], ["media_assets.asset_id"]),
        sa.ForeignKeyConstraint(["tap_id"], ["taps.tap_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tap_id"),
    )


def downgrade() -> None:
    op.drop_table("tap_display_configs")

    with op.batch_alter_table("beverages") as batch_op:
        batch_op.drop_constraint("fk_beverages_logo_asset_id_media_assets", type_="foreignkey")
        batch_op.drop_constraint("fk_beverages_background_asset_id_media_assets", type_="foreignkey")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("price_display_mode_default")
        batch_op.drop_column("text_theme")
        batch_op.drop_column("logo_asset_id")
        batch_op.drop_column("background_asset_id")
        batch_op.drop_column("accent_color")
        batch_op.drop_column("display_brand_name")
        batch_op.drop_column("ibu")
        batch_op.drop_column("description_short")

    op.drop_index(op.f("ix_media_assets_checksum_sha256"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_kind"), table_name="media_assets")
    op.drop_table("media_assets")
