"""Create tenant Catalog categories and explicit Product membership."""

from alembic import op
import sqlalchemy as sa

revision = "0013_catalog_categories"
down_revision = "0012_catalog_simple"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_catalog_categories"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["catalog_categories.id"],
            name="fk_catalog_categories_parent",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_catalog_categories_parent_id", "catalog_categories", ["parent_id"]
    )
    op.create_table(
        "catalog_category_contents",
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint(
            "category_id", "locale_code", name="pk_catalog_category_contents"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["catalog_categories.id"],
            name="fk_catalog_category_contents_category",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_category_contents_name",
        ),
    )
    op.create_table(
        "catalog_product_categories",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column(
            "is_primary", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.PrimaryKeyConstraint(
            "product_id", "category_id", name="pk_catalog_product_categories"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["catalog_products.id"],
            name="fk_catalog_product_categories_product",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["catalog_categories.id"],
            name="fk_catalog_product_categories_category",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_catalog_product_categories_category_id",
        "catalog_product_categories",
        ["category_id"],
    )
    op.create_index(
        "uq_catalog_product_categories_primary",
        "catalog_product_categories",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_catalog_product_categories_primary", table_name="catalog_product_categories"
    )
    op.drop_index(
        "ix_catalog_product_categories_category_id",
        table_name="catalog_product_categories",
    )
    op.drop_table("catalog_product_categories")
    op.drop_table("catalog_category_contents")
    op.drop_index("ix_catalog_categories_parent_id", table_name="catalog_categories")
    op.drop_table("catalog_categories")
