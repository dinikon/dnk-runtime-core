from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


class OutboundMessagePublisherProtocol(Protocol):
    """Port enqueueing outbound-message delivery work into an operational queue."""

    async def publish(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        source: str,
        published_at: datetime,
    ) -> None:
        """Enqueues one communication outbound message job."""
        ...


__all__ = [
    "OutboundMessagePublisherProtocol",
]
