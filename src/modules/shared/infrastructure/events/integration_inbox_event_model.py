from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.domain.events.inbox_event_status import InboxEventStatus
from src.modules.shared.infrastructure.persistence import Base, LongText, StringUUID


class IntegrationInboxEventModel(Base):
    """Global PostgreSQL inbox for event-consumer idempotency."""

    __tablename__ = "integration_inbox_events"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source",
            "message_id",
            name="integration_inbox_message_uq",
        ),
        Index("integration_inbox_event_type_idx", "event_type"),
    )

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=sa.text(f"'{InboxEventStatus.RECEIVED.value}'"),
        default=InboxEventStatus.RECEIVED.value,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(LongText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


__all__ = ["IntegrationInboxEventModel"]
