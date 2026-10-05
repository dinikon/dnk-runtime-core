"""Add Catalog attributes and VARIABLE product variants."""

from alembic import op
import sqlalchemy as sa

revision = "0013_catalog_variable"
down_revision = "0012_catalog_simple"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_catalog_products_type", "catalog_products", type_="check")
    op.create_check_constraint(
        "ck_catalog_products_type",
        "catalog_products",
        "type IN ('SIMPLE', 'VARIABLE')",
    )
    op.create_unique_constraint(
        "uq_catalog_products_id_type", "catalog_products", ["id", "type"]
    )
    op.add_column(
        "catalog_variants",
        sa.Column(
            "product_type", sa.String(16), nullable=False, server_default="SIMPLE"
        ),
    )
    op.add_column(
        "catalog_variants",
        sa.Column(
            "combination_key", sa.Text(), nullable=False, server_default="SIMPLE"
        ),
    )
    op.alter_column("catalog_variants", "product_type", server_default=None)
    op.alter_column("catalog_variants", "combination_key", server_default=None)
    op.drop_constraint(
        "fk_catalog_variants_product", "catalog_variants", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_catalog_variants_product", "catalog_variants", type_="unique"
    )
    op.create_foreign_key(
        "fk_catalog_variants_product_type",
        "catalog_variants",
        "catalog_products",
        ["product_id", "product_type"],
        ["id", "type"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_catalog_variants_combination",
        "catalog_variants",
        ["product_id", "combination_key"],
    )
    op.create_index(
        "uq_catalog_variants_simple_product",
        "catalog_variants",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("product_type = 'SIMPLE'"),
    )
    op.create_table(
        "catalog_attributes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_catalog_attributes"),
        sa.UniqueConstraint("code", name="uq_catalog_attributes_code"),
        sa.CheckConstraint("type = 'SELECT'", name="ck_catalog_attributes_type"),
    )
    op.create_table(
        "catalog_attribute_options",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_attribute_options"),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["catalog_attributes.id"],
            name="fk_catalog_attribute_options_attribute",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "attribute_id", "code", name="uq_catalog_attribute_options_code"
        ),
        sa.UniqueConstraint(
            "id", "attribute_id", name="uq_catalog_attribute_options_id_attribute"
        ),
    )
    op.create_table(
        "catalog_attribute_contents",
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint(
            "attribute_id", "locale_code", name="pk_catalog_attribute_contents"
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["catalog_attributes.id"],
            name="fk_catalog_attribute_contents_attribute",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_attribute_contents_name",
        ),
    )
    op.create_table(
        "catalog_option_contents",
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint(
            "option_id", "locale_code", name="pk_catalog_option_contents"
        ),
        sa.ForeignKeyConstraint(
            ["option_id"],
            ["catalog_attribute_options.id"],
            name="fk_catalog_option_contents_option",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_option_contents_name",
        ),
    )
    op.create_table(
        "catalog_variant_selections",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint(
            "variant_id", "attribute_id", name="pk_catalog_variant_selections"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["catalog_variants.id"],
            name="fk_catalog_variant_selections_variant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["option_id", "attribute_id"],
            ["catalog_attribute_options.id", "catalog_attribute_options.attribute_id"],
            name="fk_catalog_variant_selections_option_attribute",
        ),
    )


def downgrade() -> None:
    op.drop_table("catalog_variant_selections")
    op.drop_table("catalog_option_contents")
    op.drop_table("catalog_attribute_contents")
    op.drop_table("catalog_attribute_options")
    op.drop_table("catalog_attributes")
    op.drop_index("uq_catalog_variants_simple_product", table_name="catalog_variants")
    op.drop_constraint(
        "uq_catalog_variants_combination", "catalog_variants", type_="unique"
    )
    op.drop_constraint(
        "fk_catalog_variants_product_type", "catalog_variants", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_catalog_variants_product",
        "catalog_variants",
        "catalog_products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_catalog_variants_product", "catalog_variants", ["product_id"]
    )
    op.drop_column("catalog_variants", "combination_key")
    op.drop_column("catalog_variants", "product_type")
    op.drop_constraint(
        "uq_catalog_products_id_type", "catalog_products", type_="unique"
    )
    op.drop_constraint("ck_catalog_products_type", "catalog_products", type_="check")
    op.create_check_constraint(
        "ck_catalog_products_type", "catalog_products", "type = 'SIMPLE'"
    )
