from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockDocumentReturnModel(TenantBase):
    """Хранит собственные параметры RETURN без правил жизненного цикла."""

    __tablename__ = "stock_document_returns"
    __table_args__ = (
        sa.Index("ix_document_returns_origin", "origin_execution_id"),
        sa.ForeignKeyConstraint(
            ["origin_execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_document_return_origin",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("document_id", name="pk_stock_document_returns"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["tenant.stock_documents.id"],
            name="fk_document_return_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "direction IN ('FROM_RECIPIENT','TO_SUPPLIER')",
            name="ck_document_return_direction",
        ),
    )
    document_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    direction: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text(), nullable=False)

    origin_execution_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
