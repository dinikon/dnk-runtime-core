from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ReceiptCostAllocationModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_receipt_cost_allocations"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "evidence_id", "execution_line_id", name="pk_stock_receipt_cost_allocations"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["tenant.stock_receipt_cost_evidence.id"],
            name="fk_receipt_allocation_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_line_id"],
            ["tenant.stock_execution_lines.id"],
            name="fk_receipt_allocation_line",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "amount >= 0 AND amount != 'NaN'::numeric",
            name="ck_receipt_allocation_amount",
        ),
    )
    evidence_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    execution_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(19, 4), nullable=False)
