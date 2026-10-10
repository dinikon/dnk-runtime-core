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
        sa.CheckConstraint("status IN ('uploading', 'ready')", name="ck_files_status"),
        sa.Index("ix_files_bucket_status", "bucket_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    bucket_id: Mapped[UUID] = mapped_column(sa.ForeignKey("tenant.files_buckets.id"))
    object_key: Mapped[str] = mapped_column(sa.String(32))
    name: Mapped[str] = mapped_column(sa.String(255))
    content_type: Mapped[str] = mapped_column(sa.String(255))
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[str] = mapped_column(sa.String(20))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
