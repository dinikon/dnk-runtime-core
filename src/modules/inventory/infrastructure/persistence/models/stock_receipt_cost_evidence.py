from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ReceiptCostEvidenceModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_receipt_cost_evidence"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_receipt_cost_evidence"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_receipt_cost_execution",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "total_amount >= 0 AND total_amount != 'NaN'::numeric",
            name="ck_receipt_cost_amount",
        ),
        sa.CheckConstraint(
            "basis_kind IN ('MANUAL','EXTERNAL')", name="ck_receipt_cost_basis"
        ),
        sa.Index("ix_receipt_cost_execution", "execution_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    basis_kind: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    source_system: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
