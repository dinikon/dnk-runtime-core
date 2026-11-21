from uuid import UUID
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class WriteOffPostingRequestModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_write_off_posting_requests"
    __table_args__ = (
        sa.PrimaryKeyConstraint("key", name="pk_stock_write_off_posting_requests"),
        sa.UniqueConstraint("execution_id", name="uq_write_off_request_execution"),
        sa.UniqueConstraint("posting_id", name="uq_write_off_request_posting"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["tenant.stock_executions.id"],
            name="fk_write_off_request_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["tenant.stock_postings.id"],
            name="fk_write_off_request_posting",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(execution_id IS NULL AND posting_id IS NULL AND result IS NULL) OR (execution_id IS NOT NULL AND posting_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_write_off_request_result",
        ),
    )
    key: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    execution_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    posting_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    result: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
