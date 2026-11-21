"""Удаление базовой валюты tenant после отключения её использования в профиле.

Старые API и provisioning-процессы должны завершить работу до upgrade.
Downgrade восстанавливает пустую структуру; настройки возвращаются из резервной копии.
"""

from alembic import op
import sqlalchemy as sa

revision = "0018_remove_currency_settings"
down_revision = "0017_remove_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет только таблицу валютных настроек текущего tenant без CASCADE."""
    op.drop_table("tenant_currency_settings")


def downgrade() -> None:
    """Восстанавливает пустую историческую таблицу без подстановки базовой валюты."""
    op.create_table(
        "tenant_currency_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "id = '00000000-0000-0000-0000-000000000001'",
            name="ck_tenant_currency_settings_singleton",
        ),
    )
