"""Удаление моделей хранения Channels из tenant-схем."""

from alembic import op

revision = "0027_remove_channels"
down_revision = "0025_user_display_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет публикации, запуски импорта и подключения текущего tenant без CASCADE."""
    op.drop_table("channel_publications")
    op.drop_table("channel_publication_import_runs")
    op.drop_table("channels")


def downgrade() -> None:
    """Восстанавливает историческую структуру без credentials, публикаций и прогресса."""
    scripts = op.get_context().script
    if scripts is None:
        raise RuntimeError("Для восстановления схемы нужна история Alembic.")
    revisions = tuple(
        scripts.get_revision(revision_id)
        for revision_id in ("0013_channels", "0014_channel_publications")
    )
    if any(revision is None for revision in revisions):
        raise RuntimeError("Исторические ревизии Channels не найдены.")
    for revision in revisions:
        revision.module.upgrade()
