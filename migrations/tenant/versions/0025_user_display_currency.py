"""Предпочтение валюты профиля в таблице пользователей каждой tenant-схемы."""

from alembic import op
import sqlalchemy as sa

revision = "0025_user_display_currency"
down_revision = "0024_currency_exchange_rates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет nullable-код; существующие пользователи наследуют валюту Tenant."""
    op.add_column("users", sa.Column("display_currency", sa.String(3), nullable=True))


def downgrade() -> None:
    """Удаляет только новое предпочтение профиля при откате ревизии."""
    op.drop_column("users", "display_currency")
