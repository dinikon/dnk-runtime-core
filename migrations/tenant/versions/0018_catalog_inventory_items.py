"""Заменяет самостоятельные коды каталога ссылками на складскую номенклатуру."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018_catalog_inventory_items"
down_revision = "0017_inventory_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Очищает прежние SKU без backfill и устанавливает защиту ссылок в tenant."""
    op.drop_index("uq_catalog_item_sku", table_name="catalog_item")
    op.drop_column("catalog_item", "sku")
    op.add_column(
        "catalog_item",
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_catalog_item_inventory_item",
        "catalog_item",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_catalog_item_inventory_item",
        "catalog_item",
        ["inventory_item_id"],
        unique=True,
        postgresql_where=sa.text("inventory_item_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_catalog_item_inventory_role",
        "catalog_item",
        "kind<>'variable' OR inventory_item_id IS NULL",
    )


def downgrade() -> None:
    """Восстанавливает пустое текстовое поле; удалённые старые коды не возвращаются."""
    op.drop_constraint("ck_catalog_item_inventory_role", "catalog_item", type_="check")
    op.drop_index("uq_catalog_item_inventory_item", table_name="catalog_item")
    op.drop_constraint(
        "fk_catalog_item_inventory_item", "catalog_item", type_="foreignkey"
    )
    op.drop_column("catalog_item", "inventory_item_id")
    op.add_column("catalog_item", sa.Column("sku", sa.String(128), nullable=True))
    op.create_index(
        "uq_catalog_item_sku",
        "catalog_item",
        ["sku"],
        unique=True,
        postgresql_where=sa.text("sku IS NOT NULL"),
    )
