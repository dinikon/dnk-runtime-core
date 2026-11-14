"""Серийные экземпляры SKU и защита принадлежности партии."""

from alembic import op
import sqlalchemy as sa

revision = "0023_inventory_stock_serials"
down_revision = "0022_inventory_stock_lots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт экземпляры без дат, точную уникальность номера и защитные FK."""
    op.create_unique_constraint(
        "uq_stock_lots_item_id", "stock_lots", ["inventory_item_id", "id"]
    )
    op.create_table(
        "stock_serials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Text(collation="C"), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_stock_serials"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_stock_serials_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id", "lot_id"],
            ["stock_lots.inventory_item_id", "stock_lots.id"],
            name="fk_stock_serials_item_lot",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "number", name="uq_stock_serials_item_number"
        ),
        sa.CheckConstraint(
            "char_length(btrim(number)) > 0", name="ck_stock_serials_number"
        ),
    )
    op.create_index(
        "ix_stock_serials_item_lot", "stock_serials", ["inventory_item_id", "lot_id"]
    )


def downgrade() -> None:
    """Удаляет только серийные экземпляры и вспомогательный уникальный ключ партии."""
    op.drop_table("stock_serials")
    op.drop_constraint("uq_stock_lots_item_id", "stock_lots", type_="unique")
