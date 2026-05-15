from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.modules.communication.application.outbound_message.ports import (
    OutboundMessagePublisherProtocol,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
    OutboundMessageIdVO,
)
from src.modules.shared import EntityIdVO


class OutboundQueueRepositoryProtocol(Protocol):

    async def list_publishable_outbounds(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        now: datetime,
        republish_before: datetime,
    ) -> list[OutboundMessage]: ...

    async def mark_outbound_published(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        published_at: datetime,
    ) -> None: ...

    async def recover_stuck_outbounds(
        self,
        *,
        tenant_id: EntityIdVO,
        older_than: datetime,
        now: datetime,
        limit: int,
    ) -> int: ...


__all__ = [
    "OutboundMessagePublisherProtocol",
    "OutboundQueueRepositoryProtocol",
]
