from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockPositionModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_positions"
    __table_args__ = (
        sa.Index(
            "ix_positions_serial",
            "serial_id",
            "id",
            postgresql_where=sa.text("serial_id IS NOT NULL"),
        ),
        sa.Index(
            "ix_positions_lot",
            "lot_id",
            "id",
            postgresql_where=sa.text("lot_id IS NOT NULL"),
        ),
        sa.Index("ix_positions_owner_item", "owner_id", "inventory_item_id", "id"),
        sa.Index(
            "ix_positions_location_owner_item",
            "location_id",
            "owner_id",
            "inventory_item_id",
            "id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_positions"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_stock_positions_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["tenant.stock_locations.id"],
            name="fk_stock_positions_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["tenant.stock_lots.id"],
            name="fk_stock_positions_lot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["serial_id"],
            ["tenant.stock_serials.id"],
            name="fk_stock_positions_serial",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id",
            "location_id",
            "owner_id",
            "lot_id",
            "serial_id",
            "stock_status",
            name="uq_stock_positions_dimensions",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "on_hand_qty >= 0 AND on_hand_qty NOT IN ('NaN'::numeric,'Infinity'::numeric) AND (serial_id IS NULL OR on_hand_qty IN (0,1))",
            name="ck_stock_positions_quantity",
        ),
        sa.CheckConstraint("version >= 0", name="ck_stock_positions_version"),
        sa.CheckConstraint(
            "stock_status IN ('SELLABLE','QUARANTINE','DAMAGED','BLOCKED')",
            name="ck_stock_positions_status",
        ),
        sa.Index("ix_stock_positions_item", "inventory_item_id"),
        sa.Index(
            "uq_stock_positions_serial_positive",
            "serial_id",
            unique=True,
            postgresql_where=sa.text("on_hand_qty > 0 AND serial_id IS NOT NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    location_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    lot_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    serial_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    stock_status: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    base_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    on_hand_qty: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    version: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
