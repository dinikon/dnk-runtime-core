from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from src.modules.communication.application.outbound_message.queue.command import (
    PublishQueuedOutboundMessagesCommand,
    RecoverStuckOutboundMessagesCommand,
)
from src.modules.communication.application.outbound_message.queue.dto import (
    PublishQueuedResultDTO,
    RecoverStuckResultDTO,
)
from src.modules.communication.application.outbound_message.queue.ports import (
    OutboundMessagePublisherProtocol,
    OutboundQueueRepositoryProtocol,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class PublishQueuedOutboundMessagesUseCase:
    """Publishes queued outbound messages to the broker."""

    def __init__(
        self,
        *,
        repository: OutboundQueueRepositoryProtocol,
        publisher: OutboundMessagePublisherProtocol,
        republish_after_seconds: int,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._republish_after_seconds = republish_after_seconds
        self._clock = clock

    async def __call__(
        self,
        command: PublishQueuedOutboundMessagesCommand,
    ) -> PublishQueuedResultDTO:
        now = self._clock.now()
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        outbounds = await self._repository.list_publishable_outbounds(
            tenant_id=tenant_id,
            limit=command.limit,
            now=now,
            republish_before=now - timedelta(seconds=self._republish_after_seconds),
        )
        published = 0
        failed = 0
        for outbound in outbounds:
            try:
                await self._publisher.publish(
                    tenant_id=command.tenant_id,
                    outbound_message_id=_id_uuid(outbound.outbound_message_id),
                    published_at=now,
                    source=command.source,
                )
                await self._repository.mark_outbound_published(
                    tenant_id=tenant_id,
                    outbound_message_id=OutboundMessageIdVO.from_value(
                        _id_uuid(outbound.outbound_message_id)
                    ),
                    published_at=now,
                )
                published += 1
            except Exception:
                failed += 1
        return PublishQueuedResultDTO(
            scanned=len(outbounds),
            published=published,
            failed=failed,
        )


class RecoverStuckOutboundMessagesUseCase:
    """Marks expired SENDING messages as UNKNOWN for manual recovery."""

    def __init__(
        self,
        repository: OutboundQueueRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def __call__(
        self,
        command: RecoverStuckOutboundMessagesCommand,
    ) -> RecoverStuckResultDTO:
        now = self._clock.now()
        recovered = await self._repository.recover_stuck_outbounds(
            tenant_id=EntityIdVO.from_value(command.tenant_id),
            older_than=now - timedelta(seconds=command.older_than_seconds),
            now=now,
            limit=command.limit,
        )
        return RecoverStuckResultDTO(recovered=recovered)


def _id_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if hasattr(value, "uuid"):
        return value.uuid
    raise TypeError("Communication id value must expose UUID.")


__all__ = [
    "PublishQueuedOutboundMessagesUseCase",
    "RecoverStuckOutboundMessagesUseCase",
]
