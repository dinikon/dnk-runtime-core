"""Create the first tenant-scoped Catalog SIMPLE product tables."""

from alembic import op
import sqlalchemy as sa

revision = "0012_catalog_simple"
down_revision = "0011_inventory_skus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт Product, единственный Variant и локализованный контент."""
    op.create_table(
        "catalog_products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_products"),
        sa.CheckConstraint("type = 'SIMPLE'", name="ck_catalog_products_type"),
    )
    op.create_table(
        "catalog_variants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("sku_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_variants"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["catalog_products.id"],
            name="fk_catalog_variants_product",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("product_id", name="uq_catalog_variants_product"),
    )
    op.create_index("ix_catalog_variants_sku_id", "catalog_variants", ["sku_id"])
    op.create_table(
        "catalog_product_contents",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint(
            "product_id", "locale_code", name="pk_catalog_product_contents"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["catalog_products.id"],
            name="fk_catalog_product_contents_product",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_product_contents_name",
        ),
    )


def downgrade() -> None:
    """Удаляет только таблицы первого среза Catalog."""
    op.drop_table("catalog_product_contents")
    op.drop_index("ix_catalog_variants_sku_id", table_name="catalog_variants")
    op.drop_table("catalog_variants")
    op.drop_table("catalog_products")
