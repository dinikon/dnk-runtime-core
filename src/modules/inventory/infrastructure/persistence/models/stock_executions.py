from uuid import UUID
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockExecutionModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_executions"
    __table_args__ = (
        sa.Index("ix_executions_time", "executed_at", "id"),
        sa.PrimaryKeyConstraint("id", name="pk_stock_executions"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["tenant.stock_documents.id"],
            name="fk_stock_executions_document",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["tenant.warehouses.id"],
            name="fk_stock_executions_warehouse",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("document_version >= 0", name="ck_stock_executions_version"),
        sa.Index("ix_stock_executions_document", "document_id", "executed_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    document_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    document_version: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    operation_type: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
