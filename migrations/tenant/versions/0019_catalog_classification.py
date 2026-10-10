"""Общие enum-значения и классификация без изменения существующих карточек."""

from alembic import op
import sqlalchemy as sa

revision = "0019_catalog_classification"
down_revision = "0018_catalog_variable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет справочники и назначения с FK, CHECK и уникальными индексами."""
    op.create_table(
        "catalog_categories",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["parent_id"], ["catalog_categories.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("revision>0", name="ck_catalog_category_revision"),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name="ck_catalog_category_parent"
        ),
    )
    op.create_index(
        "ix_catalog_categories_parent_id", "catalog_categories", ["parent_id"]
    )
    op.create_table(
        "catalog_tags",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("revision>0", name="ck_catalog_tag_revision"),
    )
    op.create_table(
        "catalog_category_translations",
        sa.Column("category_id", sa.UUID(), primary_key=True),
        sa.Column("locale", sa.String(64), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["catalog_categories.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_category_translation_label",
        ),
    )
    op.create_table(
        "catalog_tag_translations",
        sa.Column("tag_id", sa.UUID(), primary_key=True),
        sa.Column("locale", sa.String(64), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["catalog_tags.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_tag_translation_label",
        ),
    )
    op.create_table(
        "catalog_product_categories",
        sa.Column("product_id", sa.UUID(), primary_key=True),
        sa.Column("category_id", sa.UUID(), primary_key=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["catalog_categories.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "uq_catalog_primary_category",
        "catalog_product_categories",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.create_index(
        "ix_catalog_product_categories_category_id",
        "catalog_product_categories",
        ["category_id"],
    )
    op.create_table(
        "catalog_product_tags",
        sa.Column("product_id", sa.UUID(), primary_key=True),
        sa.Column("tag_id", sa.UUID(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["catalog_tags.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_catalog_product_tags_tag_id", "catalog_product_tags", ["tag_id"]
    )
    op.create_table(
        "catalog_product_attribute_values",
        sa.Column("product_id", sa.UUID(), primary_key=True),
        sa.Column("attribute_id", sa.UUID(), primary_key=True),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id", "option_id"],
            ["catalog_attribute_options.attribute_id", "catalog_attribute_options.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "product_id", "position", name="uq_catalog_attribute_value_position"
        ),
        sa.CheckConstraint("position>=0", name="ck_catalog_attribute_value_position"),
    )
    op.create_index(
        "ix_catalog_product_attribute_values_option_id",
        "catalog_product_attribute_values",
        ["option_id"],
    )


def downgrade() -> None:
    """Удаляет части среза, оставляя контент и SIMPLE/VARIABLE прежнего head."""
    for name in (
        "catalog_product_attribute_values",
        "catalog_product_tags",
        "catalog_product_categories",
        "catalog_tag_translations",
        "catalog_category_translations",
        "catalog_tags",
        "catalog_categories",
    ):
        op.drop_table(name)
