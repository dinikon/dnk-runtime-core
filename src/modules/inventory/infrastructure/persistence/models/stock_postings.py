from uuid import UUID
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockPostingModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_postings"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_postings"),
        sa.UniqueConstraint("execution_id", name="uq_stock_postings_execution"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_stock_postings_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"],
            ["tenant.stock_postings.id"],
            name="fk_stock_postings_reversal",
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    operation_type: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    reversal_of_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
