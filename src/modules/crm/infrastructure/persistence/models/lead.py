import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class LeadModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Статическое хранение самостоятельного агрегата Lead."""

    __tablename__ = "crm_leads"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["funnel_id", "stage_id"],
            ["tenant.funnel_stages.funnel_id", "tenant.funnel_stages.id"],
            name="fk_lead_stage",
        ),
        sa.CheckConstraint("position_revision>0", name="ck_lead_position_revision"),
        sa.Index("ix_lead_kanban", "funnel_id", "stage_id", "updated_at", "id"),
        sa.CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 255", name="ck_lead_title"
        ),
    )
    title: Mapped[str] = mapped_column(sa.String(255))
    funnel_id: Mapped[UUID] = mapped_column(StringUUID)
    stage_id: Mapped[UUID] = mapped_column(StringUUID)
    position_revision: Mapped[int] = mapped_column(sa.Integer, default=1)
    first_name: Mapped[str | None] = mapped_column(sa.String(255))
    last_name: Mapped[str | None] = mapped_column(sa.String(255))
    middle_name: Mapped[str | None] = mapped_column(sa.String(255))
    company_name: Mapped[str | None] = mapped_column(sa.String(255))
    contact_id: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.contacts.id", ondelete="SET NULL")
    )
    company_id: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.companies.id", ondelete="SET NULL")
    )
    conversion_result: Mapped[dict | None] = mapped_column(sa.JSON(none_as_null=True))
    conversion_key: Mapped[str | None] = mapped_column(sa.String(200))
    conversion_fingerprint: Mapped[str | None] = mapped_column(sa.String(64))
