from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.shared.domain.events.outbox_event import OutboxEvent


class OutboxRepositoryProtocol(Protocol):
    """Persistence port for integration outbox events."""

    async def add(self, event: IntegrationEvent) -> None:
        """Stores an event in the current UnitOfWork."""
        ...

    async def claim_due_events(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> list[OutboxEvent]:
        """Claims due pending events for publication."""
        ...

    async def mark_published(
        self,
        *,
        event_id: UUID,
        published_at: datetime,
    ) -> None:
        """Marks a claimed event as published."""
        ...

    async def mark_publish_failed(
        self,
        *,
        event_id: UUID,
        error: str,
        next_attempt_at: datetime | None,
    ) -> None:
        """Marks a claimed event as failed or pending retry."""
        ...


__all__ = ["OutboxRepositoryProtocol"]
