"""Удаляет валютную метку цен и устаревшие сопоставления импорта в tenant-схеме."""

from alembic import op

revision = "0019_catalog_price_amounts"
down_revision = "0018_remove_currency_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Сохраняет суммы и даты скидок, удаляет колонку и цели импорта валюты."""
    op.drop_constraint("ck_catalog_item_price", "catalog_item", type_="check")
    op.drop_column("catalog_item", "currency")
    op.create_check_constraint(
        "ck_catalog_item_price",
        "catalog_item",
        "(regular_price IS NOT NULL AND regular_price>=0) OR "
        "(regular_price IS NULL AND sale_price IS NULL AND date_on_sale_from IS NULL "
        "AND date_on_sale_to IS NULL)",
    )
    op.execute("""
        UPDATE catalog_imports AS imports
        SET status = 'failed',
            error = 'Импорт сопоставлял только удалённое поле валюты.',
            finished_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE imports.status IN ('queued', 'running')
          AND imports.configuration->'mappings' @> '[{"target":"currency"}]'::jsonb
          AND NOT EXISTS (
              SELECT 1 FROM jsonb_array_elements(imports.configuration->'mappings') AS entries(mapping)
              WHERE mapping->>'target' IS DISTINCT FROM 'currency'
          )
        """)
    op.execute("""
        UPDATE catalog_imports AS imports
        SET configuration = jsonb_set(
            imports.configuration,
            '{mappings}',
            (SELECT COALESCE(jsonb_agg(mapping ORDER BY position), '[]'::jsonb)
             FROM jsonb_array_elements(imports.configuration->'mappings')
                  WITH ORDINALITY AS entries(mapping, position)
             WHERE mapping->>'target' IS DISTINCT FROM 'currency')
        )
        WHERE imports.configuration->'mappings' @> '[{"target":"currency"}]'::jsonb
        """)
    op.execute("""
        UPDATE catalog_imports AS imports
        SET analysis = jsonb_set(
            imports.analysis,
            '{mapped_samples}',
            (SELECT jsonb_agg(sample - 'currency' ORDER BY position)
             FROM jsonb_array_elements(imports.analysis->'mapped_samples')
                  WITH ORDINALITY AS samples(sample, position))
        )
        WHERE EXISTS (
            SELECT 1 FROM jsonb_array_elements(imports.analysis->'mapped_samples') AS samples(sample)
            WHERE sample ? 'currency'
        )
        """)


def downgrade() -> None:
    """Останавливает откат, поскольку исходные валюты цен больше не хранятся."""
    raise RuntimeError(
        "Миграция цен каталога необратима. Восстановите резервную копию."
    )
