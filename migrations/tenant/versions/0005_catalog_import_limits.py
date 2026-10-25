"""Настраиваемое число активных импортов одного tenant."""

from alembic import op
import sqlalchemy as sa

revision = "0005_catalog_import_limits"
down_revision = "0004_catalog_import_resume"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Заменяет фиксированный SQL-лимит индексом для транзакционной проверки настройки."""
    op.drop_index("uq_catalog_import_executing", table_name="catalog_imports")
    op.create_index(
        "ix_catalog_import_executing",
        "catalog_imports",
        ["id"],
        postgresql_where=sa.text("status IN ('queued','running','cancelling')"),
    )


def downgrade() -> None:
    """Восстанавливает старый лимит только после завершения лишних активных импортов."""
    active = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM catalog_imports WHERE status IN ('queued','running','cancelling')"
        )
    )
    if active > 1:
        raise RuntimeError(
            "Cannot downgrade catalog import limits while multiple imports are active. Stop or finish imports first."
        )
    op.drop_index("ix_catalog_import_executing", table_name="catalog_imports")
    op.create_index(
        "uq_catalog_import_executing",
        "catalog_imports",
        [sa.literal_column("(true)")],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','running','cancelling')"),
    )
