"""Складская номенклатура и уникальные штрихкоды текущего tenant."""

from alembic import op
import sqlalchemy as sa

revision = "0017_inventory_items"
down_revision = "0016_channels_connections_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт позиции и дочерние штрихкоды с атомарной уникальностью."""
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("sku", sa.String(25, collation="C"), nullable=False),
        sa.Column("base_uom", sa.String(16), nullable=False),
        sa.Column("quantity_step", sa.Numeric(), nullable=False),
        sa.Column("tracking_mode", sa.String(20), nullable=False),
        sa.Column("expiration_mode", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_items"),
        sa.UniqueConstraint("sku", name="uq_inventory_items_sku"),
        sa.CheckConstraint(
            "char_length(sku) BETWEEN 1 AND 25", name="ck_inventory_items_sku"
        ),
        sa.CheckConstraint(
            "quantity_step > 0 AND quantity_step NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_inventory_items_quantity_step",
        ),
        sa.CheckConstraint(
            "tracking_mode IN ('NONE', 'LOT', 'SERIAL', 'LOT_AND_SERIAL')",
            name="ck_inventory_items_tracking_mode",
        ),
        sa.CheckConstraint(
            "expiration_mode IN ('NONE', 'OPTIONAL', 'REQUIRED')",
            name="ck_inventory_items_expiration_mode",
        ),
    )
    op.create_table(
        "inventory_item_barcodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("barcode", sa.Text(collation="C"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_item_barcodes"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_inventory_item_barcodes_item",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("barcode", name="uq_inventory_item_barcodes_barcode"),
        sa.UniqueConstraint(
            "inventory_item_id", "position", name="uq_inventory_item_barcodes_position"
        ),
        sa.CheckConstraint(
            "char_length(barcode) > 0", name="ck_inventory_item_barcodes_barcode"
        ),
        sa.CheckConstraint("position >= 0", name="ck_inventory_item_barcodes_position"),
    )


def downgrade() -> None:
    """Удаляет таблицы среза в порядке их зависимостей."""
    op.drop_table("inventory_item_barcodes")
    op.drop_table("inventory_items")
