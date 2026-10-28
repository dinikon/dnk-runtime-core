import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ChannelModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Заголовок агрегата в tenant-схеме."""

    __tablename__ = "channels"
    __table_args__ = (
        sa.CheckConstraint("revision > 0", name="ck_channels_revision"),
        sa.CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 255", name="ck_channels_name"
        ),
        sa.Index("ix_channels_list", "updated_at", "id"),
    )
    name: Mapped[str] = mapped_column(sa.String(255))
    platform_kind: Mapped[str] = mapped_column(sa.String(64))
    revision: Mapped[int] = mapped_column(sa.Integer)
