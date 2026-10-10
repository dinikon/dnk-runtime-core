"""Корзина файлов и защита состояния удаления без изменения ключей объектов."""

from alembic import op
import sqlalchemy as sa

revision = "0021_files_lifecycle"
down_revision = "0020_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет lifecycle к существующему реестру без обращения к storage."""
    for name in ("deleted_at", "purge_after", "purge_requested_at"):
        op.add_column(
            "files_registry", sa.Column(name, sa.DateTime(timezone=True), nullable=True)
        )
    for name in ("deleted_by", "purge_job_id"):
        op.add_column("files_registry", sa.Column(name, sa.Uuid(), nullable=True))
    op.drop_constraint("ck_files_status", "files_registry", type_="check")
    op.create_check_constraint(
        "ck_files_status",
        "files_registry",
        "status IN ('uploading', 'ready', 'trashed', 'purging')",
    )
    op.create_check_constraint(
        "ck_files_lifecycle",
        "files_registry",
        "(status IN ('uploading', 'ready') AND deleted_at IS NULL "
        "AND deleted_by IS NULL AND purge_after IS NULL "
        "AND purge_requested_at IS NULL AND purge_job_id IS NULL) OR "
        "(status IN ('trashed', 'purging') AND deleted_at IS NOT NULL "
        "AND deleted_by IS NOT NULL AND purge_after IS NOT NULL AND "
        "((status = 'trashed' AND purge_requested_at IS NULL AND purge_job_id IS NULL) OR "
        "(status = 'purging' AND purge_requested_at IS NOT NULL AND purge_job_id IS NOT NULL)))",
    )
    op.create_check_constraint(
        "ck_files_lifecycle_times",
        "files_registry",
        "deleted_at IS NULL OR (deleted_at >= created_at "
        "AND purge_after = deleted_at + interval '720 hours' "
        "AND (purge_requested_at IS NULL OR purge_requested_at >= deleted_at))",
    )
    op.create_index(
        "ix_files_status_created", "files_registry", ["status", "created_at", "id"]
    )
    op.create_index(
        "ix_files_bucket_status_created",
        "files_registry",
        ["bucket_id", "status", "created_at", "id"],
    )
    op.create_index(
        "ix_files_status_deleted", "files_registry", ["status", "deleted_at", "id"]
    )
    op.create_index(
        "ix_files_expired_trash",
        "files_registry",
        ["purge_after", "id"],
        postgresql_where=sa.text("status = 'trashed'"),
    )


def downgrade() -> None:
    """Не допускает потери данных корзины и блокирует конкурентные переходы."""
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE files_registry IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM files_registry WHERE status IN ('trashed', 'purging'))"
        )
    ):
        raise RuntimeError(
            "Cannot downgrade files lifecycle while trash or purge records exist."
        )
    for name in (
        "ix_files_expired_trash",
        "ix_files_status_deleted",
        "ix_files_bucket_status_created",
        "ix_files_status_created",
    ):
        op.drop_index(name, table_name="files_registry")
    for name in ("ck_files_lifecycle_times", "ck_files_lifecycle", "ck_files_status"):
        op.drop_constraint(name, "files_registry", type_="check")
    op.create_check_constraint(
        "ck_files_status", "files_registry", "status IN ('uploading', 'ready')"
    )
    for name in (
        "purge_job_id",
        "purge_requested_at",
        "purge_after",
        "deleted_by",
        "deleted_at",
    ):
        op.drop_column("files_registry", name)
