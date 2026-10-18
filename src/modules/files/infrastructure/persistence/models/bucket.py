from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class BucketModel(TenantBase):
    """Реестр физических приватных контейнеров в tenant-схеме."""

    __tablename__ = "files_buckets"
    __table_args__ = (
        sa.UniqueConstraint("provider_id", name="uq_files_provider_bucket"),
        sa.CheckConstraint(
            "status IN ('preparing', 'ready', 'purged')", name="ck_files_bucket_status"
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    provider_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("tenant.files_providers.id")
    )
    name: Mapped[str] = mapped_column(sa.String(63), unique=True)
    status: Mapped[str] = mapped_column(sa.String(20))
