from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class ExternalPublicationModel(TenantBase):
    """Описывает tenant-хранение channel_external_publications без бизнес-переходов."""

    __tablename__ = "channel_external_publications"
    __table_args__ = (
        sa.UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_channel_external_publications_identity",
        ),
        sa.Index("ix_channel_publications_list", "connection_id", "id"),
        sa.Index(
            "ix_channel_publications_sku",
            "connection_id",
            sa.text("(payload ->> 'sku')"),
        ),
        sa.Index(
            "ix_channel_publications_stock",
            "connection_id",
            sa.text("((payload -> 'stock') ->> 'status')"),
        ),
        sa.CheckConstraint(
            "observed_revision > 0",
            name="ck_channel_publications_revision",
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channel_connections.id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB(), nullable=False)
    meta: Mapped[dict[str, JsonValue]] = mapped_column(JSONB(), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    observed_revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    last_import_run_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channel_sync_runs.id"), nullable=False
    )
