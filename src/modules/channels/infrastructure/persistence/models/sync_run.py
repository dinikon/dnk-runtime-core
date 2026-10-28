"""SQL-представление запуска без правил переходов состояния."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.channels.domain.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class SyncRunModel(TenantBase):
    """Хранит агрегат синхронизации в tenant-схеме."""

    __tablename__ = "channel_sync_runs"
    __table_args__ = (
        sa.Index(
            "ix_channel_sync_runs_connection", "connection_id", "created_at", "id"
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.channel_connections.id", ondelete="CASCADE")
    )
    config_revision: Mapped[int] = mapped_column(sa.Integer)
    revision: Mapped[int] = mapped_column(sa.Integer)
    status: Mapped[str] = mapped_column(sa.String(24))
    current_job_id: Mapped[UUID] = mapped_column(StringUUID)
    checkpoint_version: Mapped[int] = mapped_column(sa.Integer)
    checkpoint: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    processed_count: Mapped[int] = mapped_column(sa.Integer)
    skipped_count: Mapped[int] = mapped_column(sa.Integer)
    pages_count: Mapped[int] = mapped_column(sa.Integer)
    automatic: Mapped[bool] = mapped_column(sa.Boolean)
    error_code: Mapped[str | None] = mapped_column(sa.String(100))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
