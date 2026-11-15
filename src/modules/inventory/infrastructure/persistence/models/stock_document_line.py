from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockDocumentLineModel(TenantBase):
    """Описывает stock_document_lines в tenant-схеме без бизнес-логики."""

    __tablename__ = "stock_document_lines"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_document_lines"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["tenant.stock_documents.id"],
            name="fk_stock_document_lines_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_stock_document_lines_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "document_id", "position", name="uq_stock_document_lines_position"
        ),
        sa.CheckConstraint("position >= 0", name="ck_stock_document_lines_position"),
        sa.CheckConstraint(
            "planned_qty > 0 AND planned_qty NOT IN ('NaN'::numeric,'Infinity'::numeric) AND source_quantity > 0 AND source_quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND factor_to_base > 0 AND factor_to_base NOT IN ('NaN'::numeric,'Infinity'::numeric) AND executed_qty >= 0 AND executed_qty <= planned_qty AND executed_qty != 'NaN'::numeric",
            name="ck_stock_document_lines_quantities",
        ),
        sa.CheckConstraint(
            "(source_system IS NULL AND source_reference IS NULL) OR (source_system IS NOT NULL AND source_reference IS NOT NULL)",
            name="ck_stock_document_lines_source",
        ),
        sa.Index("ix_stock_document_lines_item", "inventory_item_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    document_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    sku: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    base_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    planned_qty: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    source_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    source_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    factor_to_base: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    executed_qty: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    source_system: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
