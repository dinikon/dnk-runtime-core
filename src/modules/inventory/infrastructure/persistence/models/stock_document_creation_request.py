from uuid import UUID
from datetime import datetime
from typing import Any
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.shared.infrastructure.persistence.portable_json import PortableJSON
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockDocumentCreationRequestModel(TenantBase):
    """Описывает stock_document_creation_requests в tenant-схеме без бизнес-логики."""

    __tablename__ = "stock_document_creation_requests"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "actor_id", "idempotency_key", name="pk_stock_document_creation_requests"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["tenant.stock_documents.id"],
            name="fk_stock_document_creation_requests_document",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(document_id IS NULL AND result IS NULL) OR (document_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_stock_document_creation_requests_result",
        ),
    )
    actor_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
