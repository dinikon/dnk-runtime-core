from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.channels.domain.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ContentDeliveryModel(TenantBase):
    """Текущее исполнение одной цели без дублирования lease Shared Jobs."""

    __tablename__ = "channel_content_deliveries"
    __table_args__ = (
        sa.Index("ix_content_delivery_publication", "publication_id"),
        sa.Index(
            "ix_content_delivery_pending",
            "status",
            postgresql_where=sa.text("status IN ('queued', 'unknown')"),
        ),
    )
    representation_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.channel_product_representations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    publication_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.channel_external_publications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    revision: Mapped[int] = mapped_column(sa.BigInteger)
    requested_generation: Mapped[int] = mapped_column(sa.BigInteger)
    sending_generation: Mapped[int | None] = mapped_column(sa.BigInteger)
    applied_generation: Mapped[int | None] = mapped_column(sa.BigInteger)
    status: Mapped[str] = mapped_column(sa.Text)
    current_job_id: Mapped[UUID] = mapped_column(StringUUID)
    requested_context: Mapped[JsonObject] = mapped_column(JSONB)
    prepared_schema: Mapped[str | None] = mapped_column(sa.Text)
    prepared_request_encrypted: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    prepared_context: Mapped[JsonObject | None] = mapped_column(JSONB)
    prepared_hash: Mapped[str | None] = mapped_column(sa.Text)
    last_applied_hash: Mapped[str | None] = mapped_column(sa.Text)
    result: Mapped[JsonObject] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
