from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockExecutionReturnModel(TenantBase):
    """Хранит собственные параметры RETURN без правил жизненного цикла."""

    __tablename__ = "stock_execution_returns"
    __table_args__ = (
        sa.Index("ix_execution_returns_origin", "origin_execution_id"),
        sa.ForeignKeyConstraint(
            ["origin_execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_execution_return_origin",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("execution_id", name="pk_stock_execution_returns"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_execution_return_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "direction IN ('FROM_RECIPIENT','TO_SUPPLIER')",
            name="ck_execution_return_direction",
        ),
    )
    execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    direction: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text(), nullable=False)

    origin_execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
