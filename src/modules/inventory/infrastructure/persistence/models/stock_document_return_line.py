from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockDocumentReturnLineModel(TenantBase):
    """Хранит собственную связь строки возврата с исходной фактической строкой."""

    __tablename__ = "stock_document_return_lines"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "document_line_id", name="pk_stock_document_return_lines"
        ),
        sa.ForeignKeyConstraint(
            ["document_line_id"],
            ["tenant.stock_document_lines.id"],
            name="fk_document_return_line_root",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_execution_line_id"],
            ["tenant.stock_execution_lines.id"],
            name="fk_document_return_line_origin",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_document_return_lines_origin", "origin_execution_line_id"),
    )
    document_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    origin_execution_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
