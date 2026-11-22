"""Убирает признак исходного языка у категории."""

import sqlalchemy as sa
from alembic import op

revision = "0025_drop_category_source_locale"
down_revision = "0024_fb_publication_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет колонку, сохраняя все локализованные названия."""
    op.drop_column("catalog_categories", "source_locale")


def downgrade() -> None:
    """Восстанавливает обязательную колонку по первой доступной локали."""
    op.add_column(
        "catalog_categories", sa.Column("source_locale", sa.String(64), nullable=True)
    )
    op.execute("""
        UPDATE catalog_categories AS category
        SET source_locale = (
            SELECT min(translation.locale)
            FROM catalog_category_translations AS translation
            WHERE translation.category_id = category.id
        )
        """)
    op.alter_column("catalog_categories", "source_locale", nullable=False)
