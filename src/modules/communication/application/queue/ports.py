from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.communication.application.message.ports import (
    OutboundMessagePublisherProtocol,
)
from src.modules.communication.domain import OutboundMessage


class OutboundQueueRepositoryProtocol(Protocol):
    async def list_publishable_outbounds(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        now: datetime,
        republish_before: datetime,
    ) -> list[OutboundMessage]: ...

    async def mark_outbound_published(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        published_at: datetime,
    ) -> None: ...

    async def recover_stuck_outbounds(
        self,
        *,
        tenant_id: UUID,
        older_than: datetime,
        now: datetime,
        limit: int,
    ) -> int: ...


__all__ = [
    "OutboundMessagePublisherProtocol",
    "OutboundQueueRepositoryProtocol",
]
