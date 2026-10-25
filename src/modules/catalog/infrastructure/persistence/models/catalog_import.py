from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogImportModel(TenantBase):
    """Состояние запуска и ограниченный предпросмотр, без содержимого всего файла."""

    __tablename__ = "catalog_imports"
    __table_args__ = (
        sa.CheckConstraint("generation >= 0", name="ck_catalog_import_generation"),
        sa.CheckConstraint(
            "status IN ('preparing','mapping','queued','running','cancelling','cancelled','completed','completed_with_errors','failed','expired')",
            name="ck_catalog_import_status",
        ),
        sa.CheckConstraint(
            "total>=0 AND processed>=0 AND processed<=total AND created>=0 AND updated>=0 AND skipped>=0 AND errors>=0 AND warnings>=0 AND processed=created+updated+skipped+errors",
            name="ck_catalog_import_counts",
        ),
        sa.Index(
            "ix_catalog_import_executing",
            "id",
            postgresql_where=sa.text("status IN ('queued','running','cancelling')"),
        ),
        sa.Index("ix_catalog_import_created", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(sa.Uuid)
    idempotency_key: Mapped[str] = mapped_column(sa.String(200), unique=True)
    fingerprint: Mapped[str] = mapped_column(sa.String(64))
    source_name: Mapped[str] = mapped_column(sa.String(255))
    source_url: Mapped[str | None] = mapped_column(sa.Text)
    source_file_id: Mapped[UUID | None] = mapped_column(sa.Uuid)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB)
    analysis: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(sa.String(32))
    version: Mapped[int] = mapped_column(sa.Integer)
    generation: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    prepared_version: Mapped[int] = mapped_column(sa.Integer)
    total: Mapped[int] = mapped_column(sa.Integer)
    processed: Mapped[int] = mapped_column(sa.Integer)
    created: Mapped[int] = mapped_column(sa.Integer)
    updated: Mapped[int] = mapped_column(sa.Integer)
    skipped: Mapped[int] = mapped_column(sa.Integer)
    errors: Mapped[int] = mapped_column(sa.Integer)
    warnings: Mapped[int] = mapped_column(sa.Integer)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    job_id: Mapped[UUID | None] = mapped_column(sa.Uuid)
    error: Mapped[str | None] = mapped_column(sa.String(1000))
