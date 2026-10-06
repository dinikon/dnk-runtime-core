from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID


class PublicationImportRunModel(TenantBase):
    """Хранит устойчивый прогресс и ревизию подключения фонового импорта."""

    __tablename__ = "channel_publication_import_runs"
    __table_args__ = (
        sa.Index(
            "ix_publication_import_channel",
            "channel_id",
            "connection_revision",
            "created_at",
        ),
        sa.Index(
            "uq_publication_import_active",
            "channel_id",
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'running')"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed')",
            name="ck_publication_import_status",
        ),
        sa.CheckConstraint(
            "connection_revision > 0 AND pages >= 0 AND resources >= 0",
            name="ck_publication_import_progress",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pages: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    resources: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    job_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
