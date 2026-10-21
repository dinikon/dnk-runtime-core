from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class BatchExportRunModel(TenantBase):
    """Хранит отдельный lifecycle пакетного импорта и метаданные неизменяемого файла."""

    __tablename__ = "channel_batch_exports"
    __table_args__ = (
        sa.Index(
            "uq_batch_export_active_connection",
            "connection_id",
            unique=True,
            postgresql_where=sa.text(
                "status IN ('preparing','building','checking','ready','submitting','processing','verifying','unknown')"
            ),
        ),
        sa.Index("ix_batch_export_channel_created", "channel_id", "created_at", "id"),
        sa.CheckConstraint(
            "sequence >= 0 AND generation >= 0 AND attempts >= 0",
            name="ck_batch_export_counters",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_batch_export_expiration"
        ),
        sa.CheckConstraint(
            "status IN ('preparing','building','checking','ready','submitting','processing','verifying','unknown','succeeded','partial','failed','empty','prepared')",
            name="ck_batch_export_status",
        ),
        sa.CheckConstraint(
            "delivery_mode IN ('provider','file')", name="ck_batch_export_delivery_mode"
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channels.id"), nullable=False
    )
    connection_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_connections.id"), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(sa.UUID(), nullable=True)
    generation: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    trigger: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    delivery_mode: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, server_default="provider"
    )
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    sequence: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    remote_id: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    artifact_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    artifact_size: Mapped[int | None] = mapped_column(sa.BigInteger(), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    attempts: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    identity_cursor: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)


class BatchExportItemModel(TenantBase):
    """Хранит принадлежащие пакету цели и результаты, читаемые ограниченными страницами."""

    __tablename__ = "channel_batch_export_items"
    __table_args__ = (
        sa.Index("ix_batch_export_item_work", "run_id", "status", "publication_id"),
        sa.Index("ix_batch_export_item_identity", "run_id", "identity_key"),
        sa.CheckConstraint(
            "binding_revision > 0 AND identity_count BETWEEN 0 AND 2",
            name="ck_batch_export_item_counters",
        ),
        sa.CheckConstraint(
            "status IN ('pending','ready','skipped','verified','failed','unknown')",
            name="ck_batch_export_item_status",
        ),
    )
    run_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("channel_batch_exports.id", ondelete="CASCADE"),
        primary_key=True,
    )
    publication_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_publications.id"), primary_key=True
    )
    catalog_item_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    binding_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_bindings.id"), nullable=False
    )
    representation_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_product_representations.id"), nullable=False
    )
    binding_revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    provider_context: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    desired: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    baseline: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    issues: Mapped[list] = mapped_column(JSONB(), nullable=False)
    identity_key: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    identity_count: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    identity_native_ok: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
