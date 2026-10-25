import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase

from decimal import Decimal


class BasketModel(TenantBase):
    """Единственная корзина владельца и рассчитанный коммерческий итог."""

    __tablename__ = "crm_baskets"
    __table_args__ = (
        sa.UniqueConstraint(
            "owner_model_key", "owner_record_id", name="uq_crm_basket_owner"
        ),
        sa.CheckConstraint(
            "currency IN ('USD','EUR','UAH')", name="ck_crm_basket_currency"
        ),
        sa.CheckConstraint(
            "state IN ('editable','frozen') AND revision>0", name="ck_crm_basket_state"
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    owner_model_key: Mapped[str] = mapped_column(sa.String(32))
    owner_record_id: Mapped[UUID] = mapped_column(StringUUID)
    currency: Mapped[str] = mapped_column(sa.String(3))
    total: Mapped[Decimal] = mapped_column(sa.Numeric(40, 2))
    state: Mapped[str] = mapped_column(sa.String(16))
    revision: Mapped[int] = mapped_column(sa.Integer)
    source_basket_id: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.crm_baskets.id", ondelete="SET NULL")
    )
