import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class DealModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Статическое хранение самостоятельного агрегата Deal."""

    __tablename__ = "crm_deals"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["funnel_id", "stage_id"],
            ["tenant.funnel_stages.funnel_id", "tenant.funnel_stages.id"],
            name="fk_deal_stage",
        ),
        sa.CheckConstraint("position_revision>0", name="ck_deal_position_revision"),
        sa.Index("ix_deal_kanban", "funnel_id", "stage_id", "updated_at", "id"),
        sa.CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 255", name="ck_deal_title"
        ),
    )
    title: Mapped[str] = mapped_column(sa.String(255))
    funnel_id: Mapped[UUID] = mapped_column(StringUUID)
    stage_id: Mapped[UUID] = mapped_column(StringUUID)
    position_revision: Mapped[int] = mapped_column(sa.Integer, default=1)
    source_lead_id: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.crm_leads.id", ondelete="RESTRICT")
    )
    source_lead_snapshot: Mapped[dict | None] = mapped_column(
        sa.JSON(none_as_null=True)
    )
    lifecycle_state: Mapped[str] = mapped_column(sa.String(20), default="draft")
