"""Подготовка XML для ручного использования без отправки в источник."""

from alembic import op
import sqlalchemy as sa

revision = "0034_batch_export_file_delivery"
down_revision = "0033_channel_batch_exports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Сохраняет существующие пакеты в режиме provider и добавляет терминальный prepared."""
    op.add_column(
        "channel_batch_exports",
        sa.Column(
            "delivery_mode", sa.String(10), nullable=False, server_default="provider"
        ),
    )
    op.create_check_constraint(
        "ck_batch_export_delivery_mode",
        "channel_batch_exports",
        "delivery_mode IN ('provider','file')",
    )
    op.drop_constraint("ck_batch_export_status", "channel_batch_exports", type_="check")
    op.create_check_constraint(
        "ck_batch_export_status",
        "channel_batch_exports",
        "status IN ('preparing','building','checking','ready','submitting','processing','verifying','unknown','succeeded','partial','failed','empty','prepared')",
    )


def downgrade() -> None:
    """Удаляет расширение только при отсутствии файловых операций, избегая потери их смысла."""
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM channel_batch_exports WHERE delivery_mode = 'file')"
        )
    ):
        raise RuntimeError("File-only export history prevents downgrade")
    op.drop_constraint("ck_batch_export_status", "channel_batch_exports", type_="check")
    op.create_check_constraint(
        "ck_batch_export_status",
        "channel_batch_exports",
        "status IN ('preparing','building','checking','ready','submitting','processing','verifying','unknown','succeeded','partial','failed','empty')",
    )
    op.drop_constraint(
        "ck_batch_export_delivery_mode", "channel_batch_exports", type_="check"
    )
    op.drop_column("channel_batch_exports", "delivery_mode")
