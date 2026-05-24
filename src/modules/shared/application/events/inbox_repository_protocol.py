from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.shared.domain.events.integration_event import IntegrationEvent


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


__all__ = ["InboxRepositoryProtocol"]
