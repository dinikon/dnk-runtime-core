from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockExecutionLineModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_execution_lines"
    __table_args__ = (
        sa.Index("ix_execution_lines_item", "inventory_item_id", "execution_id"),
        sa.PrimaryKeyConstraint("id", name="pk_stock_execution_lines"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_stock_execution_lines_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_line_id"],
            ["tenant.stock_document_lines.id"],
            name="fk_stock_execution_lines_document_line",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_stock_execution_lines_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["tenant.stock_locations.id"],
            name="fk_stock_execution_lines_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["tenant.stock_lots.id"],
            name="fk_stock_execution_lines_lot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["serial_id"],
            ["tenant.stock_serials.id"],
            name="fk_stock_execution_lines_serial",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "execution_id", "position", name="uq_stock_execution_lines_position"
        ),
        sa.CheckConstraint(
            "quantity > 0 AND quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND source_quantity > 0 AND source_quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND factor_to_base > 0 AND factor_to_base NOT IN ('NaN'::numeric,'Infinity'::numeric) AND position >= 0",
            name="ck_stock_execution_lines_quantity",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    document_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    base_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    source_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    source_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    factor_to_base: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    location_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    lot_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    serial_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    stock_status: Mapped[str] = mapped_column(sa.Text(), nullable=False)
