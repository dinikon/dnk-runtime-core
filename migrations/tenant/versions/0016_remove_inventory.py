"""Удаление таблиц Inventory из tenant-схем."""

from alembic import op

revision = "0016_remove_inventory"
down_revision = "0015_remove_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет справочник SKU и склады текущего tenant без CASCADE."""
    op.drop_table("skus")
    op.drop_table("warehouses")


def downgrade() -> None:
    """Восстанавливает исторические таблицы и ограничения без удалённых данных."""
    scripts = op.get_context().script
    if scripts is None:
        raise RuntimeError("Для восстановления схемы нужна история Alembic.")
    revisions = tuple(
        scripts.get_revision(revision_id)
        for revision_id in ("0001_warehouses", "0011_inventory_skus")
    )
    if any(revision is None for revision in revisions):
        raise RuntimeError("Исторические ревизии Inventory не найдены.")
    for revision in revisions:
        revision.module.upgrade()
