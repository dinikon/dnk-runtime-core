from __future__ import annotations

from src.modules.shared.application.events.command import HandleIntegrationEventCommand
from src.modules.shared.application.events.dto import HandleIntegrationEventResultDTO
from src.modules.shared.kernel.events.integration_event import IntegrationEvent
from src.modules.shared.kernel.events.ports import (
    EventConsumerPort,
    InboxRepositoryProtocol,
)
from src.modules.shared.kernel.time import ClockPort


class IdempotentEventConsumer:
    """Runs an integration event handler behind inbox idempotency."""

    def __init__(
        self,
        *,
        inbox_repository: InboxRepositoryProtocol,
        handler: EventConsumerPort,
        clock: ClockPort,
    ) -> None:
        self._inbox_repository = inbox_repository
        self._handler = handler
        self._clock = clock

    async def __call__(
        self,
        command: HandleIntegrationEventCommand,
        event: IntegrationEvent,
    ) -> HandleIntegrationEventResultDTO:
        now = self._clock.now()
        first_delivery = await self._inbox_repository.record_received(
            source=command.source,
            message_id=command.message_id,
            event=event,
            received_at=now,
        )
        if not first_delivery:
            return HandleIntegrationEventResultDTO(consumed=False, duplicate=True)

        try:
            await self._handler.handle(event)
        except Exception as exc:
            await self._inbox_repository.mark_failed(
                tenant_id=event.tenant_id,
                source=command.source,
                message_id=command.message_id,
                error=str(exc),
            )
            raise

        await self._inbox_repository.mark_consumed(
            tenant_id=event.tenant_id,
            source=command.source,
            message_id=command.message_id,
            consumed_at=self._clock.now(),
        )
        return HandleIntegrationEventResultDTO(consumed=True, duplicate=False)


__all__ = ["IdempotentEventConsumer"]
