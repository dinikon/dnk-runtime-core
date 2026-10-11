"""Отдельные валютные настройки в каждой tenant-схеме."""

from alembic import op
import sqlalchemy as sa

revision = "0022_tenant_currency_settings"
down_revision = "0021_files_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт singleton настроек и начальное значение UAH для существующего Tenant."""
    op.create_table(
        "tenant_currency_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_tenant_currency_settings_singleton"),
    )
    op.execute(
        "INSERT INTO tenant_currency_settings (id, base_currency, created_at, updated_at) "
        "VALUES (1, 'UAH', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )


def downgrade() -> None:
    """Удаляет tenant-таблицу валютных настроек при откате среза."""
    op.drop_table("tenant_currency_settings")
