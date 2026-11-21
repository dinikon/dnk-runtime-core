"""Самостоятельные партии складских позиций."""

from alembic import op
import sqlalchemy as sa

revision = "0022_inventory_stock_lots"
down_revision = "0021_inventory_item_packagings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт партии, точную уникальность номера внутри SKU и защитные ограничения."""
    op.create_table(
        "stock_lots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Text(collation="C"), nullable=False),
        sa.Column("manufactured_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_stock_lots"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_stock_lots_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "number", name="uq_stock_lots_item_number"
        ),
        sa.CheckConstraint(
            "char_length(btrim(number)) > 0", name="ck_stock_lots_number"
        ),
        sa.CheckConstraint(
            "manufactured_on IS NULL OR expires_on IS NULL OR manufactured_on <= expires_on",
            name="ck_stock_lots_dates",
        ),
    )


def downgrade() -> None:
    """Удаляет только таблицу партий, сохраняя SKU."""
    op.drop_table("stock_lots")
