import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class FunnelModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Хранение определения процесса tenant."""

    __tablename__ = "funnels"
    __table_args__ = (
        sa.CheckConstraint(
            "model_key IN ('crm.lead','crm.deal')", name="ck_funnels_model_key"
        ),
        sa.CheckConstraint("revision>0", name="ck_funnels_revision"),
        sa.Index(
            "uq_funnels_default",
            "model_key",
            unique=True,
            postgresql_where=sa.text("is_default"),
        ),
    )
    model_key: Mapped[str] = mapped_column(sa.String(32))
    name: Mapped[str] = mapped_column(sa.String(150))
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    revision: Mapped[int] = mapped_column(sa.Integer, default=1)
