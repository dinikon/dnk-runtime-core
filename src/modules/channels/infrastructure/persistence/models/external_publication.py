"""SQL-снимок реальной публикации платформы."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.channels.domain.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ExternalPublicationModel(TenantBase):
    """Описывает хранение, не проверяя роли и согласованность дерева."""

    __tablename__ = "channel_external_publications"
    __table_args__ = (
        sa.UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_channel_publication_external_key",
        ),
        sa.Index("ix_channel_publications_parent", "parent_id", "id"),
        sa.Index("ix_channel_publications_connection", "connection_id", "id"),
        sa.Index("ix_channel_publications_run", "last_sync_run_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.channel_connections.id", ondelete="CASCADE")
    )
    resource_type: Mapped[str] = mapped_column(sa.String(64))
    external_id: Mapped[str] = mapped_column(sa.Text)
    kind: Mapped[str] = mapped_column(sa.String(24))
    parent_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.channel_external_publications.id",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    revision: Mapped[int] = mapped_column(sa.Integer)
    raw_data: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    normalized_schema: Mapped[str] = mapped_column(sa.String(100))
    normalized_data: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    platform_schema: Mapped[str] = mapped_column(sa.String(100))
    platform_data: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    first_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    last_sync_run_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.channel_sync_runs.id", deferrable=True, initially="DEFERRED"
        ),
    )
