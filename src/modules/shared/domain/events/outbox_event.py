from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.shared.domain.events.integration_event import IntegrationEvent


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    """Persisted integration event waiting for broker publication."""

    id: UUID
    tenant_id: UUID
    event_type: str
    event_version: int
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    occurred_at: datetime
    published_at: datetime | None
    publish_attempts: int
    status: str
    next_attempt_at: datetime | None
    last_error: str | None

    def to_integration_event(self) -> IntegrationEvent:
        """Returns the public integration event contract."""
        return IntegrationEvent(
            event_id=self.id,
            tenant_id=self.tenant_id,
            event_type=self.event_type,
            event_version=self.event_version,
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            payload=dict(self.payload),
            occurred_at=self.occurred_at,
        )


__all__ = ["OutboxEvent"]
