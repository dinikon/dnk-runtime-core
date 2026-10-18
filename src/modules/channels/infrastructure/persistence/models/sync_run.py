from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class SyncRunModel(TenantBase):
    """Описывает tenant-хранение channel_sync_runs без бизнес-переходов."""

    __tablename__ = "channel_sync_runs"
    __table_args__ = (
        sa.Index("ix_channel_runs_latest", "connection_id", "created_at", "id"),
        sa.Index(
            "uq_channel_runs_active",
            "connection_id",
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'running')"),
        ),
        sa.CheckConstraint(
            "sequence >= 0 AND processed >= 0 AND invalid >= 0 AND failures >= 0",
            name="ck_channel_runs_progress",
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False, primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channels.id"), nullable=False
    )
    connection_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channel_connections.id"), nullable=False
    )
    operation: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default=sa.text("'initialize_publications'"),
    )
    generation: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    checkpoint: Mapped[dict[str, JsonValue]] = mapped_column(JSONB(), nullable=False)
    sequence: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    processed: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    invalid: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    failures: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    limitations: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    request_keys: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
    job_id: Mapped[UUID | None] = mapped_column(sa.UUID(), nullable=True)
    read_complete: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false()
    )
