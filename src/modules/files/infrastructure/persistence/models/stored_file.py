from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StoredFileModel(TenantBase):
    """Реестр объектов, независимо от бизнес-ссылок потребителей."""

    __tablename__ = "files_registry"
    __table_args__ = (
        sa.UniqueConstraint("bucket_id", "object_key", name="uq_files_object"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_files_size"),
        sa.CheckConstraint(
            "status IN ('uploading', 'ready', 'trashed', 'purging')",
            name="ck_files_status",
        ),
        sa.CheckConstraint(
            "(status IN ('uploading', 'ready') AND deleted_at IS NULL "
            "AND deleted_by IS NULL AND purge_after IS NULL "
            "AND purge_requested_at IS NULL AND purge_job_id IS NULL) OR "
            "(status IN ('trashed', 'purging') AND deleted_at IS NOT NULL "
            "AND deleted_by IS NOT NULL AND purge_after IS NOT NULL AND "
            "((status = 'trashed' AND purge_requested_at IS NULL AND purge_job_id IS NULL) OR "
            "(status = 'purging' AND purge_requested_at IS NOT NULL AND purge_job_id IS NOT NULL)))",
            name="ck_files_lifecycle",
        ),
        sa.CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at "
            "AND purge_after = deleted_at + interval '720 hours' "
            "AND (purge_requested_at IS NULL OR purge_requested_at >= deleted_at))",
            name="ck_files_lifecycle_times",
        ),
        sa.Index("ix_files_bucket_status", "bucket_id", "status"),
        sa.Index("ix_files_status_created", "status", "created_at", "id"),
        sa.Index(
            "ix_files_bucket_status_created", "bucket_id", "status", "created_at", "id"
        ),
        sa.Index("ix_files_status_deleted", "status", "deleted_at", "id"),
        sa.Index(
            "ix_files_expired_trash",
            "purge_after",
            "id",
            postgresql_where=sa.text("status = 'trashed'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    bucket_id: Mapped[UUID] = mapped_column(sa.ForeignKey("tenant.files_buckets.id"))
    object_key: Mapped[str] = mapped_column(sa.String(32))
    name: Mapped[str] = mapped_column(sa.String(255))
    content_type: Mapped[str] = mapped_column(sa.String(255))
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[str] = mapped_column(sa.String(20))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    deleted_by: Mapped[UUID | None] = mapped_column(sa.Uuid)
    purge_after: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    purge_requested_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    purge_job_id: Mapped[UUID | None] = mapped_column(sa.Uuid)
