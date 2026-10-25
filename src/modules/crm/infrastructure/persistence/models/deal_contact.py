import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class DealContactModel(TenantBase):
    """Связь участника продажи без объединения агрегатов."""

    __tablename__ = "crm_deal_contacts"
    deal_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.crm_deals.id", ondelete="CASCADE"),
        primary_key=True,
    )
    contact_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.contacts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
