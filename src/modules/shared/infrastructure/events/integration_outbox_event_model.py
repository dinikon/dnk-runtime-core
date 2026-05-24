from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.domain.events.outbox_event_status import OutboxEventStatus
from src.modules.shared.infrastructure.persistence import (
    Base,
    LongText,
    PortableJSON,
    StringUUID,
)


class IntegrationOutboxEventModel(Base):
    """Global PostgreSQL outbox for integration events."""

    __tablename__ = "integration_outbox_events"
    __table_args__ = (
        Index(
            "integration_outbox_due_idx",
            "status",
            "next_attempt_at",
            "occurred_at",
        ),
        Index(
            "integration_outbox_aggregate_idx",
            "tenant_id",
            "aggregate_type",
            "aggregate_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True, nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    publish_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=sa.text("0"),
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=sa.text(f"'{OutboxEventStatus.PENDING.value}'"),
        default=OutboxEventStatus.PENDING.value,
        index=True,
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_error: Mapped[str | None] = mapped_column(LongText, nullable=True)
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


__all__ = ["IntegrationOutboxEventModel"]
