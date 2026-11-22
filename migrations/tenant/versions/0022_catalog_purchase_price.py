"""Добавляет независимую закупочную цену."""

from alembic import op
import sqlalchemy as sa

revision = "0022_catalog_purchase_price"
down_revision = "0021_feed_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет колонку и снимает прежнее SQL-сравнение цен."""
    op.add_column("catalog_item", sa.Column("purchase_price", sa.Numeric()))
    op.drop_constraint(
        "ck_catalog_item_sale_price", "catalog_item", type_="check", if_exists=True
    )


def downgrade() -> None:
    """Разрешает откат до появления закупочных цен и их сопоставлений импорта."""
    op.execute("""
        LOCK TABLE catalog_item, catalog_imports IN ACCESS EXCLUSIVE MODE
        """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM catalog_item WHERE purchase_price IS NOT NULL)
               OR EXISTS (SELECT 1 FROM catalog_imports
                          WHERE configuration->'mappings' @> '[{"target":"purchase_price"}]'::jsonb) THEN
                RAISE EXCEPTION 'Откат удалит закупочные цены или их сопоставления.';
            END IF;
        END $$;
        """)
    op.drop_column("catalog_item", "purchase_price")
