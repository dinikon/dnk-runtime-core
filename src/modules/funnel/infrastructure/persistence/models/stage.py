import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class FunnelStageModel(TenantBase):
    """Внутренняя стадия процесса; порядок не является идентификатором."""

    __tablename__ = "funnel_stages"
    __table_args__ = (
        sa.UniqueConstraint("funnel_id", "id", name="uq_funnel_stage_owner"),
        sa.UniqueConstraint(
            "funnel_id",
            "position",
            name="uq_funnel_stage_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint("position>=0", name="ck_funnel_stage_position"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    funnel_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.funnels.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(sa.String(100))
    color: Mapped[str] = mapped_column(sa.String(16))
    position: Mapped[int] = mapped_column(sa.Integer)
