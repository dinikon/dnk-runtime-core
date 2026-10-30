from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ContentMediaModel(TenantBase):
    """Хранит доступ и внешний ID; порядок и alt принадлежат представлению."""

    __tablename__ = "channel_content_media"
    __table_args__ = (
        sa.UniqueConstraint(
            "connection_id",
            "file_id",
            "source_fingerprint",
            "metadata_fingerprint",
            name="uq_content_media_variant",
        ),
        sa.Index("ix_content_media_file", "file_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.channel_connections.id", ondelete="CASCADE")
    )
    file_id: Mapped[UUID] = mapped_column(StringUUID)
    source_fingerprint: Mapped[str] = mapped_column(sa.Text)
    metadata_fingerprint: Mapped[str] = mapped_column(sa.Text)
    revision: Mapped[int] = mapped_column(sa.Integer)
    access_token_hash: Mapped[bytes] = mapped_column(sa.LargeBinary)
    access_token_encrypted: Mapped[bytes] = mapped_column(sa.LargeBinary)
    access_revoked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    remote_media_id: Mapped[str | None] = mapped_column(sa.Text)
    transfer_status: Mapped[str] = mapped_column(sa.Text)
    current_operation_id: Mapped[UUID | None] = mapped_column(StringUUID)
    error_code: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
