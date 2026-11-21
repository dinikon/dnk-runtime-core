from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockExecutionStatusChangeModel(TenantBase):
    """Хранит собственные параметры STATUS_CHANGE без правил жизненного цикла."""

    __tablename__ = "stock_execution_status_changes"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "execution_id", name="pk_stock_execution_status_changes"
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_execution_status_change_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "target_status IN ('SELLABLE','QUARANTINE','DAMAGED','BLOCKED')",
            name="ck_execution_status_change_target",
        ),
    )
    execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    target_status: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text(), nullable=False)
