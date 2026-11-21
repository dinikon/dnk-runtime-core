"""Склады и самостоятельные локации с защитой принадлежности основной ссылки."""

from alembic import op
import sqlalchemy as sa

revision = "0019_inventory_warehouses"
down_revision = "0018_catalog_inventory_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт обе таблицы, затем добавляет обратный FK основной локации."""
    op.create_table(
        "warehouses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(collation="C"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("default_storage_location_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
        sa.UniqueConstraint("code", name="uq_warehouses_code"),
        sa.CheckConstraint("char_length(btrim(code)) > 0", name="ck_warehouses_code"),
        sa.CheckConstraint("char_length(btrim(name)) > 0", name="ck_warehouses_name"),
    )
    op.create_table(
        "stock_locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("parent_location_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.Text(collation="C"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("location_type", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stock_locations"),
        sa.UniqueConstraint(
            "warehouse_id", "code", name="uq_stock_locations_warehouse_code"
        ),
        sa.UniqueConstraint(
            "id", "warehouse_id", name="uq_stock_locations_id_warehouse"
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_locations_warehouse",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_location_id", "warehouse_id"],
            ["stock_locations.id", "stock_locations.warehouse_id"],
            name="fk_stock_locations_parent",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "parent_location_id <> id", name="ck_stock_locations_not_self_parent"
        ),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0", name="ck_stock_locations_code"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_stock_locations_name"
        ),
        sa.CheckConstraint(
            "location_type IN ('STORAGE', 'RECEIVING', 'SHIPPING', 'QUARANTINE', 'TRANSIT')",
            name="ck_stock_locations_type",
        ),
    )
    op.create_foreign_key(
        "fk_warehouses_default_storage_location",
        "warehouses",
        "stock_locations",
        ["default_storage_location_id", "id"],
        ["id", "warehouse_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Снимает обратный FK и удаляет только таблицы этого среза."""
    op.drop_constraint(
        "fk_warehouses_default_storage_location", "warehouses", type_="foreignkey"
    )
    op.drop_table("stock_locations")
    op.drop_table("warehouses")
