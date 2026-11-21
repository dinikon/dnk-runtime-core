from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockExecutionReturnLineModel(TenantBase):
    """Хранит собственную связь строки возврата с исходной фактической строкой."""

    __tablename__ = "stock_execution_return_lines"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "execution_line_id", name="pk_stock_execution_return_lines"
        ),
        sa.ForeignKeyConstraint(
            ["execution_line_id"],
            ["tenant.stock_execution_lines.id"],
            name="fk_execution_return_line_root",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_execution_line_id"],
            ["tenant.stock_execution_lines.id"],
            name="fk_execution_return_line_origin",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_execution_return_lines_origin", "origin_execution_line_id"),
    )
    execution_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    origin_execution_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
