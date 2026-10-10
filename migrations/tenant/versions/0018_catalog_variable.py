"""Enum-определения и VARIABLE; сохраняет существующий SIMPLE и его контент."""

from alembic import op
import sqlalchemy as sa

revision = "0018_catalog_variable"
down_revision = "0017_catalog_simple"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Расширяет структуры и добавляет нормализованные справочники и selections."""
    op.drop_constraint("ck_catalog_product_simple", "catalog_products", type_="check")
    op.create_check_constraint(
        "ck_catalog_product_kind", "catalog_products", "kind IN ('simple','variable')"
    )
    op.drop_constraint(
        "catalog_variants_product_id_key", "catalog_variants", type_="unique"
    )
    op.create_unique_constraint(
        "uq_catalog_variant_owner", "catalog_variants", ["product_id", "id"]
    )
    op.create_table(
        "catalog_attributes",
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint("revision>0", name="ck_catalog_attribute_revision"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "catalog_attribute_options",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position>=0", name="ck_catalog_option_position"),
        sa.ForeignKeyConstraint(
            ["attribute_id"], ["catalog_attributes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attribute_id", "code", name="uq_catalog_option_code"),
        sa.UniqueConstraint("attribute_id", "id", name="uq_catalog_option_owner"),
        sa.UniqueConstraint(
            "attribute_id",
            "position",
            deferrable=True,
            initially="DEFERRED",
            name="uq_catalog_option_position",
        ),
    )
    op.create_table(
        "catalog_attribute_translations",
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_attribute_translation_label",
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id"], ["catalog_attributes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("attribute_id", "locale"),
    )
    op.create_table(
        "catalog_attribute_option_translations",
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_attribute_option_translation_label",
        ),
        sa.ForeignKeyConstraint(
            ["option_id"], ["catalog_attribute_options.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("option_id", "locale"),
    )
    op.create_table(
        "catalog_product_axes",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position>=0", name="ck_catalog_axis_position"),
        sa.ForeignKeyConstraint(
            ["attribute_id"], ["catalog_attributes.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog_products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("product_id", "attribute_id"),
        sa.UniqueConstraint("product_id", "position", name="uq_catalog_axis_position"),
    )
    op.create_table(
        "catalog_product_axis_options",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attribute_id", "option_id"],
            ["catalog_attribute_options.attribute_id", "catalog_attribute_options.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "attribute_id"],
            ["catalog_product_axes.product_id", "catalog_product_axes.attribute_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", "attribute_id", "option_id"),
    )
    op.create_table(
        "catalog_product_default_selections",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id", "attribute_id", "option_id"],
            [
                "catalog_product_axis_options.product_id",
                "catalog_product_axis_options.attribute_id",
                "catalog_product_axis_options.option_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("product_id", "attribute_id"),
    )
    op.create_table(
        "catalog_variant_selections",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id", "attribute_id", "option_id"],
            [
                "catalog_product_axis_options.product_id",
                "catalog_product_axis_options.attribute_id",
                "catalog_product_axis_options.option_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "variant_id"],
            ["catalog_variants.product_id", "catalog_variants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("variant_id", "attribute_id"),
    )
    op.create_index(
        op.f("ix_catalog_variant_selections_product_id"),
        "catalog_variant_selections",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    """Возвращает SIMPLE только при отсутствии VARIABLE, не теряя существующие товары."""
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM catalog_products WHERE kind='variable')")
    ):
        raise RuntimeError(
            "Перед downgrade переведите VARIABLE в SIMPLE через сценарий Catalog."
        )
    op.drop_table("catalog_variant_selections")
    op.drop_table("catalog_product_default_selections")
    op.drop_table("catalog_product_axis_options")
    op.drop_table("catalog_product_axes")
    op.drop_table("catalog_attribute_option_translations")
    op.drop_table("catalog_attribute_translations")
    op.drop_table("catalog_attribute_options")
    op.drop_table("catalog_attributes")
    op.drop_constraint("uq_catalog_variant_owner", "catalog_variants", type_="unique")
    op.create_unique_constraint(
        "catalog_variants_product_id_key", "catalog_variants", ["product_id"]
    )
    op.drop_constraint("ck_catalog_product_kind", "catalog_products", type_="check")
    op.create_check_constraint(
        "ck_catalog_product_simple", "catalog_products", "kind='simple'"
    )
