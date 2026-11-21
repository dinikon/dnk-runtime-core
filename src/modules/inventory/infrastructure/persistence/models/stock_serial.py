from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockSerialModel(TenantBase):
    """Хранит номер экземпляра и связь с партией без собственных дат."""

    __tablename__ = "stock_serials"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_serials"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_stock_serials_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id", "lot_id"],
            ["tenant.stock_lots.inventory_item_id", "tenant.stock_lots.id"],
            name="fk_stock_serials_item_lot",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "number", name="uq_stock_serials_item_number"
        ),
        sa.CheckConstraint(
            "char_length(btrim(number)) > 0", name="ck_stock_serials_number"
        ),
        sa.Index("ix_stock_serials_item_lot", "inventory_item_id", "lot_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    number: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    lot_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
