"""Allow VARIABLE products and localized variants."""

from alembic import op
import sqlalchemy as sa

revision = "0015_catalog_variants"
down_revision = "0014_catalog_product_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_catalog_products_kind", "catalog_products", type_="check")
    op.create_check_constraint(
        "ck_catalog_products_kind", "catalog_products", "kind IN ('simple', 'variable')"
    )
    op.drop_constraint(
        "uq_catalog_variants_product", "catalog_variants", type_="unique"
    )
    op.create_unique_constraint(
        "uq_catalog_variants_product_sku",
        "catalog_variants",
        ["product_id", "sku_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_table(
        "catalog_variant_contents",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint(
            "variant_id", "locale_code", name="pk_catalog_variant_contents"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["catalog_variants.id"],
            name="fk_catalog_variant_contents_variant",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(short_description)) > 0",
            name="ck_catalog_variant_contents_description",
        ),
    )


def downgrade() -> None:
    op.drop_table("catalog_variant_contents")
    op.drop_constraint(
        "uq_catalog_variants_product_sku", "catalog_variants", type_="unique"
    )
    op.create_unique_constraint(
        "uq_catalog_variants_product", "catalog_variants", ["product_id"]
    )
    op.drop_constraint("ck_catalog_products_kind", "catalog_products", type_="check")
    op.create_check_constraint(
        "ck_catalog_products_kind", "catalog_products", "kind = 'simple'"
    )
