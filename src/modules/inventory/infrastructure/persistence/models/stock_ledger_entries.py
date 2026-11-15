from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockLedgerEntryModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_ledger_entries"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_ledger_entries"),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["tenant.stock_postings.id"],
            name="fk_ledger_posting",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["tenant.stock_positions.id"],
            name="fk_ledger_position",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "posting_id", "position_id", name="uq_ledger_posting_position"
        ),
        sa.UniqueConstraint("posting_id", "position", name="uq_ledger_ordinal"),
        sa.CheckConstraint(
            "quantity_delta NOT IN (0,'NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND source_quantity > 0 AND source_quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND factor_to_base > 0 AND factor_to_base NOT IN ('NaN'::numeric,'Infinity'::numeric)",
            name="ck_ledger_quantities",
        ),
        sa.Index("ix_ledger_position", "position_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    posting_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    position_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    base_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    source_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    source_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    factor_to_base: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
