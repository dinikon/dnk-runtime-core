from __future__ import annotations

from datetime import timedelta

from src.modules.shared.application.events.command import PublishOutboxEventsCommand
from src.modules.shared.application.events.dto import PublishOutboxResultDTO
from src.modules.shared.kernel.events.ports import (
    EventPublisherPort,
    OutboxRepositoryProtocol,
)
from src.modules.shared.kernel.time import ClockPort


class PublishOutboxEventsUseCase:
    """Publishes due integration events from PostgreSQL outbox to the broker."""

    def __init__(
        self,
        *,
        repository: OutboxRepositoryProtocol,
        publisher: EventPublisherPort,
        clock: ClockPort,
        retry_base_seconds: int,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._clock = clock
        self._retry_base_seconds = retry_base_seconds

    async def __call__(
        self,
        command: PublishOutboxEventsCommand,
    ) -> PublishOutboxResultDTO:
        now = self._clock.now()
        events = await self._repository.claim_due_events(
            limit=command.limit,
            now=now,
        )
        published = 0
        failed = 0
        for outbox_event in events:
            try:
                await self._publisher.publish(outbox_event.to_integration_event())
                await self._repository.mark_published(
                    event_id=outbox_event.id,
                    published_at=now,
                )
                published += 1
            except Exception as exc:
                next_attempt_at = None
                if outbox_event.publish_attempts < command.max_attempts:
                    next_attempt_at = now + timedelta(
                        seconds=self._retry_base_seconds
                        * max(1, outbox_event.publish_attempts)
                    )
                await self._repository.mark_publish_failed(
                    event_id=outbox_event.id,
                    error=str(exc),
                    next_attempt_at=next_attempt_at,
                )
                failed += 1
        return PublishOutboxResultDTO(
            scanned=len(events),
            published=published,
            failed=failed,
        )


__all__ = ["PublishOutboxEventsUseCase"]
