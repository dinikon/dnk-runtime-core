"""Удаление таблиц локального Catalog перед разработкой новой модели."""

from alembic import op

revision = "0015_remove_catalog"
down_revision = "0014_channel_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет только таблицы Catalog в порядке зависимостей без CASCADE."""
    for table_name in (
        "catalog_product_categories",
        "catalog_category_contents",
        "catalog_categories",
        "catalog_variant_content_values",
        "catalog_product_content_values",
        "catalog_variant_contents",
        "catalog_product_contents",
        "catalog_variants",
        "catalog_products",
        "catalog_product_type_content_blocks",
        "catalog_product_type_translations",
        "catalog_product_types",
        "catalog_content_block_translations",
        "catalog_content_block_definitions",
    ):
        op.drop_table(table_name)


def downgrade() -> None:
    """Восстанавливает историческую схему и seed, но не удалённые данные."""
    scripts = op.get_context().script
    if scripts is None:
        raise RuntimeError("Для восстановления схемы нужна история Alembic.")
    historical_revision = scripts.get_revision("0012_catalog")
    if historical_revision is None:
        raise RuntimeError("Историческая ревизия 0012_catalog не найдена.")
    historical_revision.module.upgrade()
