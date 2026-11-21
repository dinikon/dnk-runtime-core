from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class InventoryItemModel(TenantBase):
    """Хранит настройки складской позиции в схеме текущего tenant."""

    __tablename__ = "inventory_items"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_inventory_items"),
        sa.UniqueConstraint("sku", name="uq_inventory_items_sku"),
        sa.CheckConstraint(
            "char_length(sku) BETWEEN 1 AND 25", name="ck_inventory_items_sku"
        ),
        sa.CheckConstraint(
            "quantity_step > 0 AND quantity_step NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_inventory_items_quantity_step",
        ),
        sa.CheckConstraint(
            "tracking_mode IN ('NONE', 'LOT', 'SERIAL', 'LOT_AND_SERIAL')",
            name="ck_inventory_items_tracking_mode",
        ),
        sa.CheckConstraint(
            "expiration_mode IN ('NONE', 'OPTIONAL', 'REQUIRED')",
            name="ck_inventory_items_expiration_mode",
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    sku: Mapped[str] = mapped_column(sa.String(25, collation="C"), nullable=False)
    base_uom: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    quantity_step: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    tracking_mode: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    expiration_mode: Mapped[str] = mapped_column(sa.String(20), nullable=False)
