"""Дерево локализованных категорий и назначения корневых карточек."""

import sqlalchemy as sa
from alembic import op
from uuid6 import uuid7

revision = "0023_catalog_categories"
down_revision = "0022_catalog_purchase_price"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт начальную категорию отдельно в каждой схеме, включая новые tenant."""
    op.create_table(
        "catalog_categories",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("parent_id", sa.UUID(), sa.ForeignKey("catalog_categories.id")),
        sa.Column("source_locale", sa.String(64), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_catalog_categories_parent_id", "catalog_categories", ["parent_id"]
    )
    translations = op.create_table(
        "catalog_category_translations",
        sa.Column(
            "category_id",
            sa.UUID(),
            sa.ForeignKey("catalog_categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("locale", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )
    op.create_table(
        "catalog_item_categories",
        sa.Column(
            "catalog_item_id",
            sa.UUID(),
            sa.ForeignKey("catalog_item.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            sa.UUID(),
            sa.ForeignKey("catalog_categories.id"),
            primary_key=True,
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_catalog_item_categories_category_id",
        "catalog_item_categories",
        ["category_id"],
    )
    default_id = uuid7()
    db = op.get_bind()
    db.execute(
        sa.text(
            "INSERT INTO catalog_categories (id, source_locale, is_default) VALUES (:id,'ru',true)"
        ),
        {"id": default_id},
    )
    db.execute(
        translations.insert(),
        [
            dict(category_id=default_id, locale=locale, name=name)
            for locale, name in (
                ("ru", "Неразобранное"),
                ("uk", "Нерозібране"),
                ("en", "Uncategorized"),
            )
        ],
    )
    db.execute(
        sa.text(
            "INSERT INTO catalog_item_categories (catalog_item_id, category_id, is_default) "
            "SELECT id, :id, true FROM catalog_item WHERE parent_id IS NULL"
        ),
        {"id": default_id},
    )


def downgrade() -> None:
    """Откат удаляет добавленные таблицы только при исходном справочнике."""
    db = op.get_bind()
    if db.scalar(
        sa.text(
            """SELECT (SELECT count(*) FROM catalog_categories) <> 1
        OR EXISTS (SELECT 1 FROM catalog_item_categories WHERE NOT is_default)
        OR (SELECT jsonb_object_agg(locale,name) FROM catalog_category_translations)
        IS DISTINCT FROM '{"ru":"Неразобранное","uk":"Нерозібране","en":"Uncategorized"}'::jsonb"""
        )
    ):
        raise RuntimeError("Откат удалит пользовательские категории или переводы.")
    for table in (
        "catalog_item_categories",
        "catalog_category_translations",
        "catalog_categories",
    ):
        op.drop_table(table)
