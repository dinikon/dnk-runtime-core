"""Create the canonical tenant Catalog schema and its clean content type."""

from uuid import UUID

from alembic import op
import sqlalchemy as sa

revision = "0012_catalog"
down_revision = "0011_inventory_skus"
branch_labels = None
depends_on = None

CLEAN_ID = UUID("00000000-0000-5000-8000-000000000001")
TITLE_ID = UUID("00000000-0000-5000-8000-000000000101")
DESCRIPTION_ID = UUID("00000000-0000-5000-8000-000000000102")
SHORT_DESCRIPTION_ID = UUID("00000000-0000-5000-8000-000000000103")


def upgrade() -> None:
    op.create_table(
        "catalog_content_block_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_content_block_definitions"),
        sa.UniqueConstraint("code", name="uq_catalog_content_block_definitions_code"),
        sa.CheckConstraint(
            "type IN ('text', 'rich_text')", name="ck_catalog_content_block_type"
        ),
    )
    op.create_table(
        "catalog_content_block_translations",
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint(
            "block_id", "locale_code", name="pk_catalog_content_block_translations"
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["catalog_content_block_definitions.id"],
            name="fk_catalog_content_block_translations_block",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_content_block_translation_name",
        ),
    )
    op.create_table(
        "catalog_product_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_product_types"),
        sa.UniqueConstraint("code", name="uq_catalog_product_types_code"),
    )
    op.create_table(
        "catalog_product_type_translations",
        sa.Column("product_type_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint(
            "product_type_id",
            "locale_code",
            name="pk_catalog_product_type_translations",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["catalog_product_types.id"],
            name="fk_catalog_product_type_translations_type",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_product_type_translation_name",
        ),
    )
    op.create_table(
        "catalog_product_type_content_blocks",
        sa.Column("product_type_id", sa.UUID(), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "product_type_id",
            "scope",
            "block_id",
            name="pk_catalog_product_type_content_blocks",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["catalog_product_types.id"],
            name="fk_catalog_product_type_blocks_type",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["catalog_content_block_definitions.id"],
            name="fk_catalog_product_type_blocks_block",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "product_type_id",
            "scope",
            "position",
            name="uq_catalog_product_type_blocks_position",
        ),
        sa.CheckConstraint(
            "scope IN ('product', 'variant')",
            name="ck_catalog_product_type_blocks_scope",
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_catalog_product_type_blocks_position"
        ),
    )
    op.create_table(
        "catalog_products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("product_type_id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "kind IN ('simple', 'variable')", name="ck_catalog_products_kind"
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["catalog_product_types.id"],
            name="fk_catalog_products_product_type",
            ondelete="RESTRICT",
        ),
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
        sa.UniqueConstraint(
            "product_id",
            "sku_id",
            name="uq_catalog_variants_product_sku",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_catalog_variants_sku_id", "catalog_variants", ["sku_id"])
    op.create_table(
        "catalog_product_contents",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint(
            "product_id", "locale_code", name="pk_catalog_product_contents"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["catalog_products.id"],
            name="fk_catalog_product_contents_product",
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "catalog_variant_contents",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint(
            "variant_id", "locale_code", name="pk_catalog_variant_contents"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["catalog_variants.id"],
            name="fk_catalog_variant_contents_variant",
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "catalog_product_content_values",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint(
            "product_id",
            "locale_code",
            "block_id",
            name="pk_catalog_product_content_values",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "locale_code"],
            [
                "catalog_product_contents.product_id",
                "catalog_product_contents.locale_code",
            ],
            name="fk_catalog_product_content_values_content",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["catalog_content_block_definitions.id"],
            name="fk_catalog_product_content_values_block",
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "catalog_variant_content_values",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("locale_code", sa.String(64), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint(
            "variant_id",
            "locale_code",
            "block_id",
            name="pk_catalog_variant_content_values",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id", "locale_code"],
            [
                "catalog_variant_contents.variant_id",
                "catalog_variant_contents.locale_code",
            ],
            name="fk_catalog_variant_content_values_content",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["catalog_content_block_definitions.id"],
            name="fk_catalog_variant_content_values_block",
            ondelete="RESTRICT",
        ),
    )
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

    definitions = sa.table(
        "catalog_content_block_definitions",
        sa.column("id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("type", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        definitions,
        [
            {"id": TITLE_ID, "code": "title", "type": "text", "is_system": True},
            {
                "id": DESCRIPTION_ID,
                "code": "description",
                "type": "rich_text",
                "is_system": True,
            },
            {
                "id": SHORT_DESCRIPTION_ID,
                "code": "short_description",
                "type": "rich_text",
                "is_system": True,
            },
        ],
    )
    block_names = sa.table(
        "catalog_content_block_translations",
        sa.column("block_id", sa.UUID()),
        sa.column("locale_code", sa.String()),
        sa.column("name", sa.String()),
    )
    op.bulk_insert(
        block_names,
        [
            {"block_id": block, "locale_code": locale, "name": name}
            for block, names in (
                (TITLE_ID, {"uk": "Назва", "ru": "Название", "en": "Title"}),
                (DESCRIPTION_ID, {"uk": "Опис", "ru": "Описание", "en": "Description"}),
                (
                    SHORT_DESCRIPTION_ID,
                    {
                        "uk": "Короткий опис",
                        "ru": "Краткое описание",
                        "en": "Short description",
                    },
                ),
            )
            for locale, name in names.items()
        ],
    )
    types = sa.table(
        "catalog_product_types",
        sa.column("id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("is_system", sa.Boolean()),
        sa.column("schema_version", sa.Integer()),
    )
    op.bulk_insert(
        types,
        [{"id": CLEAN_ID, "code": "clean", "is_system": True, "schema_version": 1}],
    )
    type_names = sa.table(
        "catalog_product_type_translations",
        sa.column("product_type_id", sa.UUID()),
        sa.column("locale_code", sa.String()),
        sa.column("name", sa.String()),
    )
    op.bulk_insert(
        type_names,
        [
            {"product_type_id": CLEAN_ID, "locale_code": "uk", "name": "Чистий"},
            {"product_type_id": CLEAN_ID, "locale_code": "ru", "name": "Чистый"},
            {"product_type_id": CLEAN_ID, "locale_code": "en", "name": "Clean"},
        ],
    )
    assignments = sa.table(
        "catalog_product_type_content_blocks",
        sa.column("product_type_id", sa.UUID()),
        sa.column("scope", sa.String()),
        sa.column("block_id", sa.UUID()),
        sa.column("required", sa.Boolean()),
        sa.column("position", sa.Integer()),
    )
    op.bulk_insert(
        assignments,
        [
            {
                "product_type_id": CLEAN_ID,
                "scope": scope,
                "block_id": block,
                "required": scope == "product" and block == TITLE_ID,
                "position": position,
            }
            for scope in ("product", "variant")
            for position, block in enumerate(
                (TITLE_ID, DESCRIPTION_ID, SHORT_DESCRIPTION_ID)
            )
        ],
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
    op.drop_table("catalog_variant_content_values")
    op.drop_table("catalog_product_content_values")
    op.drop_table("catalog_variant_contents")
    op.drop_table("catalog_product_contents")
    op.drop_index("ix_catalog_variants_sku_id", table_name="catalog_variants")
    op.drop_table("catalog_variants")
    op.drop_table("catalog_products")
    op.drop_table("catalog_product_type_content_blocks")
    op.drop_table("catalog_product_type_translations")
    op.drop_table("catalog_product_types")
    op.drop_table("catalog_content_block_translations")
    op.drop_table("catalog_content_block_definitions")
