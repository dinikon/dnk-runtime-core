from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


class OutboundMessagePublisherProtocol(Protocol):
    """Port публикации outbound-message work в broker."""

    async def publish(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        source: str,
        published_at: datetime,
    ) -> None:
        """Публикует communication outbound message job."""
        ...


__all__ = [
    "OutboundMessagePublisherProtocol",
]
