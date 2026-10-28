"""Разрешает SKU контейнера для будущей конвертации типов Catalog."""

from alembic import op
import sqlalchemy as sa

revision = "0008_catalog_variants"
down_revision = "0007_channels_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Разрешает SKU variable, сохраняя общую уникальность и хранение остатков."""
    op.drop_constraint("ck_catalog_item_sku_role", "catalog_item", type_="check")


def downgrade() -> None:
    """Восстанавливает запрет без автоматического удаления SKU."""
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM catalog_item WHERE kind='variable' AND sku IS NOT NULL LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError("Перед откатом очистите SKU вариативных карточек.")
    op.create_check_constraint(
        "ck_catalog_item_sku_role", "catalog_item", "kind<>'variable' OR sku IS NULL"
    )
