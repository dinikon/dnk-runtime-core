from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StorageProviderModel(TenantBase):
    """Tenant-хранение подключений без credentials системного провайдера."""

    __tablename__ = "files_providers"
    __table_args__ = (
        sa.CheckConstraint(
            "NOT is_system OR (kind = 'minio' AND config_ref = 'system_minio')",
            name="ck_files_system_config",
        ),
        sa.Index(
            "uq_files_system_provider",
            "is_system",
            unique=True,
            postgresql_where=sa.text("is_system"),
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(200))
    kind: Mapped[str] = mapped_column(sa.String(64))
    is_system: Mapped[bool] = mapped_column(sa.Boolean)
    config_ref: Mapped[str] = mapped_column(sa.String(200))
