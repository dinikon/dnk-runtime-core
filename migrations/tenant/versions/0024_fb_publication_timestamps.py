"""Согласует значения дат публикации по умолчанию с AudienceMixin."""

from alembic import op
import sqlalchemy as sa

revision = "0024_fb_publication_timestamps"
down_revision = "0023_catalog_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Устанавливает значения по умолчанию для новых публикаций."""
    for column in ("created_at", "updated_at"):
        op.alter_column(
            "fb_publications", column, server_default=sa.text("CURRENT_TIMESTAMP")
        )


def downgrade() -> None:
    """Возвращает прежнее определение колонок, сохраняя записанные даты."""
    for column in ("created_at", "updated_at"):
        op.alter_column("fb_publications", column, server_default=None)
