"""Удаление товарных интеграций Channels с сохранением подключений.

Удалённые данные восстанавливаются только из резервной копии. API и worker
предыдущей версии должны быть остановлены до применения этой ревизии.
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_channels_connections_only"
down_revision = "0015_channels_feed_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет только товарные таблицы текущего tenant и устаревшие настройки."""
    op.drop_table("channel_content_deliveries")
    op.drop_table("channel_content_feeds")
    op.drop_table("channel_content_media")
    op.drop_table("channel_product_representations")
    op.drop_table("channel_stock_sync_states")
    op.drop_table("channel_catalog_binding_items")
    op.drop_table("channel_catalog_binding_groups")
    op.drop_table("channel_external_publications")
    op.drop_table("channel_sync_runs")
    op.execute(
        sa.text(
            "UPDATE channel_connections SET settings = "
            "settings - 'stock_sync' - 'currency' - 'locales' - 'locale'"
        )
    )


def downgrade() -> None:
    """Запрещает откат, который не способен восстановить удалённые данные."""
    raise RuntimeError(
        "Очистка Channels необратима. Для отката восстановите резервную копию БД."
    )
