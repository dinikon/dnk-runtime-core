"""Fresh CatalogItem baseline; перенос данных старого Catalog не предусмотрен."""

from alembic import op
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
import sqlalchemy as sa

revision = "0023_catalog_item"
down_revision = "0022_tenant_currency_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт структуру Catalog без системных значений; их создаёт onboarding."""
    op.create_table(
        "catalog_content_block_definitions",
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "value_type IN ('text','rich_text')", name="ck_catalog_block_value_type"
        ),
        sa.CheckConstraint("revision>0", name="ck_content_block_revision"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "catalog_product_types",
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("revision>0", name="ck_product_type_revision"),
        sa.CheckConstraint("schema_version>0", name="ck_catalog_type_version"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "catalog_content_block_translations",
        sa.Column("content_block_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_content_block_translation_label",
        ),
        sa.ForeignKeyConstraint(
            ["content_block_id"],
            ["catalog_content_block_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("content_block_id", "locale"),
    )
    op.create_table(
        "catalog_item",
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("parent_id", StringUUID(), nullable=True),
        sa.Column(
            "required_parent_kind",
            sa.String(length=20),
            sa.Computed(
                "CASE WHEN kind='variant' THEN 'variable' ELSE NULL END", persisted=True
            ),
            nullable=True,
        ),
        sa.Column("product_type_id", StringUUID(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("virtual", sa.Boolean(), nullable=False),
        sa.Column("weight", sa.Numeric(), nullable=True),
        sa.Column("weight_unit", sa.String(length=2), nullable=True),
        sa.Column("regular_price", sa.Numeric(), nullable=True),
        sa.Column("sale_price", sa.Numeric(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("date_on_sale_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_on_sale_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("length", sa.Numeric(), nullable=True),
        sa.Column("length_unit", sa.String(length=2), nullable=True),
        sa.Column("width", sa.Numeric(), nullable=True),
        sa.Column("width_unit", sa.String(length=2), nullable=True),
        sa.Column("height", sa.Numeric(), nullable=True),
        sa.Column("height_unit", sa.String(length=2), nullable=True),
        sa.Column("manage_stock", sa.Boolean(), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=True),
        sa.Column("stock_status", sa.String(length=20), nullable=True),
        sa.Column("backorders", sa.String(length=10), nullable=False),
        sa.Column("id", StringUUID(), nullable=False),
        sa.Column("created_by", StringUUID(), nullable=False),
        sa.Column("updated_by", StringUUID(), nullable=False),
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
        sa.CheckConstraint(
            "(height IS NULL AND height_unit IS NULL) OR (height IS NOT NULL AND height_unit IS NOT NULL AND height_unit IN ('cm','m') AND height>=0 AND height NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND height * (CASE WHEN height_unit='m' THEN 1000 ELSE 10 END) = trunc(height * (CASE WHEN height_unit='m' THEN 1000 ELSE 10 END), 6))",
            name="ck_catalog_item_height",
        ),
        sa.CheckConstraint(
            "(kind='variant' AND parent_id IS NOT NULL AND parent_id<>id AND product_type_id IS NULL) OR (kind IN ('simple','variable') AND parent_id IS NULL AND product_type_id IS NOT NULL)",
            name="ck_catalog_item_role",
        ),
        sa.CheckConstraint(
            "(length IS NULL AND length_unit IS NULL) OR (length IS NOT NULL AND length_unit IS NOT NULL AND length_unit IN ('cm','m') AND length>=0 AND length NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND length * (CASE WHEN length_unit='m' THEN 1000 ELSE 10 END) = trunc(length * (CASE WHEN length_unit='m' THEN 1000 ELSE 10 END), 6))",
            name="ck_catalog_item_length",
        ),
        sa.CheckConstraint(
            "(manage_stock=true AND stock_quantity IS NOT NULL AND stock_status IS NULL AND backorders IN ('no','notify','yes')) OR (manage_stock=false AND stock_quantity IS NULL AND stock_status IS NOT NULL AND stock_status IN ('in_stock','out_of_stock','on_backorder') AND backorders='no')",
            name="ck_catalog_item_stock",
        ),
        sa.CheckConstraint(
            "(regular_price IS NOT NULL AND regular_price>=0 AND currency IS NOT NULL AND currency ~ '^[A-Z]{3}$') OR (regular_price IS NULL AND currency IS NULL AND sale_price IS NULL AND date_on_sale_from IS NULL AND date_on_sale_to IS NULL)",
            name="ck_catalog_item_price",
        ),
        sa.CheckConstraint(
            "(weight IS NULL AND weight_unit IS NULL) OR (weight IS NOT NULL AND weight_unit IS NOT NULL AND weight_unit IN ('g','kg') AND weight>=0 AND weight NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND weight * (CASE WHEN weight_unit='kg' THEN 1000 ELSE 1 END) = trunc(weight * (CASE WHEN weight_unit='kg' THEN 1000 ELSE 1 END), 6))",
            name="ck_catalog_item_weight",
        ),
        sa.CheckConstraint(
            "(width IS NULL AND width_unit IS NULL) OR (width IS NOT NULL AND width_unit IS NOT NULL AND width_unit IN ('cm','m') AND width>=0 AND width NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND width * (CASE WHEN width_unit='m' THEN 1000 ELSE 10 END) = trunc(width * (CASE WHEN width_unit='m' THEN 1000 ELSE 10 END), 6))",
            name="ck_catalog_item_width",
        ),
        sa.CheckConstraint(
            "kind IN ('simple','variable','variant')", name="ck_catalog_item_kind"
        ),
        sa.CheckConstraint(
            "kind<>'variable' OR (virtual=false AND regular_price IS NULL)",
            name="ck_catalog_item_variable_values",
        ),
        sa.CheckConstraint(
            "kind<>'variable' OR sku IS NULL", name="ck_catalog_item_sku_role"
        ),
        sa.CheckConstraint(
            "regular_price IS NULL OR (regular_price NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(regular_price)<=6)",
            name="ck_catalog_item_regular_price_precision",
        ),
        sa.CheckConstraint(
            "sale_price IS NULL OR (sale_price NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(sale_price)<=6)",
            name="ck_catalog_item_sale_price_precision",
        ),
        sa.CheckConstraint(
            "status IN ('draft','active','archived')", name="ck_catalog_item_status"
        ),
        sa.CheckConstraint(
            "(sale_price IS NULL AND date_on_sale_from IS NULL AND date_on_sale_to IS NULL) OR (sale_price IS NOT NULL AND sale_price>=0 AND sale_price<=regular_price)",
            name="ck_catalog_item_sale_price",
        ),
        sa.CheckConstraint(
            "date_on_sale_from IS NULL OR date_on_sale_to IS NULL OR date_on_sale_from<=date_on_sale_to",
            name="ck_catalog_item_sale_interval",
        ),
        sa.CheckConstraint("revision>0", name="ck_catalog_item_revision"),
        sa.ForeignKeyConstraint(
            ["parent_id", "required_parent_kind"],
            ["catalog_item.id", "catalog_item.kind"],
            name="fk_catalog_item_parent_role",
            ondelete="CASCADE",
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"], ["catalog_product_types.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "kind", name="uq_catalog_item_id_kind"),
        sa.UniqueConstraint("parent_id", "id", name="uq_catalog_item_parent_id"),
    )
    op.create_index(
        op.f("ix_catalog_item_parent_id"), "catalog_item", ["parent_id"], unique=False
    )
    op.create_index(
        "ix_catalog_item_roots",
        "catalog_item",
        ["created_at", "id"],
        unique=False,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_catalog_item_sku",
        "catalog_item",
        ["sku"],
        unique=True,
        postgresql_where=sa.text("sku IS NOT NULL"),
    )
    op.create_table(
        "catalog_product_type_content_blocks",
        sa.Column("product_type_id", sa.UUID(), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position>=0", name="ck_catalog_type_block_position"),
        sa.ForeignKeyConstraint(
            ["block_id"], ["catalog_content_block_definitions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"], ["catalog_product_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("product_type_id", "block_id"),
        sa.UniqueConstraint(
            "product_type_id", "position", name="uq_catalog_type_block_position"
        ),
    )
    op.create_table(
        "catalog_product_type_translations",
        sa.Column("product_type_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_product_type_translation_label",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"], ["catalog_product_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("product_type_id", "locale"),
    )
    op.create_table(
        "catalog_item_galleries",
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("primary_image_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["catalog_item.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("catalog_item_id", "locale"),
    )
    op.create_table(
        "catalog_item_translations",
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["catalog_item.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("catalog_item_id", "locale"),
    )
    op.create_table(
        "catalog_item_content_values",
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(mode='set' AND value IS NOT NULL) OR (mode='clear' AND value IS NULL)",
            name="ck_catalog_item_content_mode",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"], ["catalog_content_block_definitions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "locale"],
            [
                "catalog_item_translations.catalog_item_id",
                "catalog_item_translations.locale",
            ],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("catalog_item_id", "locale", "block_id"),
    )
    op.create_table(
        "catalog_item_images",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("alt", sa.String(length=1000), nullable=False),
        sa.Column("caption", sa.String(length=5000), nullable=False),
        sa.CheckConstraint("position>=0", name="ck_catalog_image_position"),
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "locale"],
            ["catalog_item_galleries.catalog_item_id", "catalog_item_galleries.locale"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "catalog_item_id", "locale", "file_id", name="uq_catalog_image_file"
        ),
        sa.UniqueConstraint(
            "catalog_item_id", "locale", "id", name="uq_catalog_image_owner"
        ),
        sa.UniqueConstraint(
            "catalog_item_id", "locale", "position", name="uq_catalog_image_position"
        ),
    )
    op.create_index(
        op.f("ix_catalog_item_images_file_id"),
        "catalog_item_images",
        ["file_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_catalog_gallery_primary",
        "catalog_item_galleries",
        "catalog_item_images",
        ["catalog_item_id", "locale", "primary_image_id"],
        ["catalog_item_id", "locale", "id"],
        initially="DEFERRED",
        deferrable=True,
        use_alter=True,
    )


def downgrade() -> None:
    """Удаляет только новый Catalog без восстановления старых таблиц."""
    op.drop_constraint(
        "fk_catalog_gallery_primary", "catalog_item_galleries", type_="foreignkey"
    )
    op.drop_table("catalog_item_images")
    op.drop_table("catalog_item_content_values")
    op.drop_table("catalog_item_translations")
    op.drop_table("catalog_item_galleries")
    op.drop_table("catalog_product_type_translations")
    op.drop_table("catalog_product_type_content_blocks")
    op.drop_table("catalog_item")
    op.drop_table("catalog_content_block_translations")
    op.drop_table("catalog_product_types")
    op.drop_table("catalog_content_block_definitions")
