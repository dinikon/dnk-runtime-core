from datetime import date
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockLotModel(TenantBase):
    """Хранит самостоятельную партию с точным номером и календарными датами."""

    __tablename__ = "stock_lots"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_lots"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_stock_lots_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("inventory_item_id", "id", name="uq_stock_lots_item_id"),
        sa.UniqueConstraint(
            "inventory_item_id", "number", name="uq_stock_lots_item_number"
        ),
        sa.CheckConstraint(
            "char_length(btrim(number)) > 0", name="ck_stock_lots_number"
        ),
        sa.CheckConstraint(
            "manufactured_on IS NULL OR expires_on IS NULL OR manufactured_on <= expires_on",
            name="ck_stock_lots_dates",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    number: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    manufactured_on: Mapped[date | None] = mapped_column(sa.Date(), nullable=True)
    expires_on: Mapped[date | None] = mapped_column(sa.Date(), nullable=True)
