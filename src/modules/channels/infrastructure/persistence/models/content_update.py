from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ContentUpdateRunModel(TenantBase):
    """Хранит lifecycle подтверждённого контентного обновления одного подключения."""

    __tablename__ = "channel_content_update_runs"
    __table_args__ = (
        sa.CheckConstraint(
            "revision > 0 AND sequence >= 0 AND generation >= 0 AND sdk_version > 0",
            name="ck_content_update_revision",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_content_update_expiration"
        ),
        sa.CheckConstraint(
            "status IN ('preparing','ready','blocked','queued','running','succeeded','partial','failed','stale')",
            name="ck_content_update_status",
        ),
        sa.Index("ix_content_update_channel_created", "channel_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channels.id"), nullable=False
    )
    connection_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_connections.id"), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    generation: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    sdk_version: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    sequence: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    preview_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
