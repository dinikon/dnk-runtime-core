from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.shared.kernel.events.integration_event import IntegrationEvent
from src.modules.shared.kernel.events.models import OutboxEvent


class EventPublisherPort(Protocol):
    """Port for publishing integration events to an external broker."""

    async def publish(self, event: IntegrationEvent) -> None:
        """Publishes one integration event."""
        ...


class EventConsumerPort(Protocol):
    """Port implemented by business integration-event handlers."""

    async def handle(self, event: IntegrationEvent) -> None:
        """Handles one integration event."""
        ...


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


class InboxRepositoryProtocol(Protocol):
    """Persistence port for consumer idempotency records."""

    async def record_received(
        self,
        *,
        source: str,
        message_id: str,
        event: IntegrationEvent,
        received_at: datetime,
    ) -> bool:
        """Returns True only for the first delivery of a message."""
        ...

    async def mark_consumed(
        self,
        *,
        tenant_id: UUID,
        source: str,
        message_id: str,
        consumed_at: datetime,
    ) -> None:
        """Marks a delivery as consumed."""
        ...

    async def mark_failed(
        self,
        *,
        tenant_id: UUID,
        source: str,
        message_id: str,
        error: str,
    ) -> None:
        """Stores the handler error for a delivery."""
        ...


__all__ = [
    "EventConsumerPort",
    "EventPublisherPort",
    "InboxRepositoryProtocol",
    "OutboxRepositoryProtocol",
]
