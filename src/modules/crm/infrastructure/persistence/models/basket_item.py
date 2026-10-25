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


class BasketItemModel(TenantBase):
    """Внутренняя коммерческая строка; собственного репозитория нет."""

    __tablename__ = "crm_basket_items"
    __table_args__ = (
        sa.UniqueConstraint(
            "basket_id",
            "position",
            name="uq_crm_basket_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint(
            "kind IN ('product','service') AND quantity>0 AND unit_price>=0 AND position>=0",
            name="ck_crm_basket_item",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    basket_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.crm_baskets.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(sa.Integer)
    name: Mapped[str] = mapped_column(sa.String(255))
    kind: Mapped[str] = mapped_column(sa.String(16))
    catalog_item_id: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.catalog_item.id", ondelete="SET NULL")
    )
    sku: Mapped[str | None] = mapped_column(sa.String(128))
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(24, 6))
    unit: Mapped[str] = mapped_column(sa.String(32))
    unit_price: Mapped[Decimal] = mapped_column(sa.Numeric(24, 6))
    line_total: Mapped[Decimal] = mapped_column(sa.Numeric(40, 2))
    custom_fields: Mapped[dict] = mapped_column(sa.JSON)
