"""Удаление заданий товарных интеграций Channels из общей очереди."""

from alembic import op
import sqlalchemy as sa

revision = "0002_channels_jobs_cleanup"
down_revision = "0001_global_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет точные типы заданий, сохраняя проверки подключений и outbox."""
    op.execute(
        sa.text(
            "DELETE FROM public.scheduled_jobs WHERE job_type IN ("
            "'channels.sync_publications', 'channels.sync_stock', "
            "'channels.deliver_content', 'channels.apply_content_feed', "
            "'catalog.stock_changed')"
        )
    )


def downgrade() -> None:
    """Не допускает имитацию восстановления удалённых заданий."""
    raise RuntimeError(
        "Очистка заданий Channels необратима. Для отката восстановите резервную копию БД."
    )
