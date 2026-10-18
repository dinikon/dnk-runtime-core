"""Удаление сохранённых заданий импорта выведенного из эксплуатации Channels."""

from alembic import op
import sqlalchemy as sa

revision = "0007_remove_channel_jobs"
down_revision = "0006_reference_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет только задания Channels; старые API и workers должны быть остановлены."""
    jobs = sa.table("scheduled_jobs", sa.column("job_type", sa.String), schema="public")
    op.execute(jobs.delete().where(jobs.c.job_type == "channels.publication_import"))


def downgrade() -> None:
    """Не восстанавливает удалённые задания и payload; импорт запускается заново."""
