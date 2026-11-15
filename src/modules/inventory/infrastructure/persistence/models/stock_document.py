from uuid import UUID
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockDocumentModel(TenantBase):
    """Описывает stock_documents в tenant-схеме без бизнес-логики."""

    __tablename__ = "stock_documents"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_documents"),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["tenant.warehouses.id"],
            name="fk_stock_documents_warehouse",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT')",
            name="ck_stock_documents_operation",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','CONFIRMED','PARTIALLY_EXECUTED','COMPLETED','CANCELLED')",
            name="ck_stock_documents_status",
        ),
        sa.CheckConstraint("version >= 0", name="ck_stock_documents_version"),
        sa.CheckConstraint(
            "(source_system IS NULL AND source_reference IS NULL AND source_version IS NULL) OR (source_system IS NOT NULL AND source_reference IS NOT NULL AND (source_version IS NULL OR source_version >= 0))",
            name="ck_stock_documents_source",
        ),
        sa.Index("ix_stock_documents_created", "created_at", "id"),
        sa.Index("ix_stock_documents_owner", "owner_id"),
        sa.Index("ix_stock_documents_warehouse", "warehouse_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    operation_type: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    status: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    source_system: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    source_version: Mapped[int | None] = mapped_column(sa.BigInteger(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    version: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
