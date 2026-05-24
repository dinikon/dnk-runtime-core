from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.application.events import (
    EventConsumerPort,
    IdempotentEventConsumer,
    PublishOutboxEventsUseCase,
)
from src.modules.shared.domain.time import ClockPort
from src.modules.shared.infrastructure.events import (
    RabbitMQIntegrationEventPublisher,
    SqlAlchemyInboxRepository,
    SqlAlchemyOutboxRepository,
)
from src.modules.shared.infrastructure.time import UtcClock


def build_outbox_repository(session: AsyncSession) -> SqlAlchemyOutboxRepository:
    """Builds the shared SQLAlchemy outbox repository for an active UoW session."""
    return SqlAlchemyOutboxRepository(session)


def build_inbox_repository(session: AsyncSession) -> SqlAlchemyInboxRepository:
    """Builds the shared SQLAlchemy inbox repository for an active UoW session."""
    return SqlAlchemyInboxRepository(session)


def build_integration_event_publisher(
    settings: EventBusSettings,
) -> RabbitMQIntegrationEventPublisher:
    """Builds a RabbitMQ-backed shared integration event publisher."""
    return RabbitMQIntegrationEventPublisher.from_settings(
        settings,
        manage_broker_lifecycle=True,
    )


def build_publish_outbox_events_use_case(
    *,
    session: AsyncSession,
    publisher: RabbitMQIntegrationEventPublisher,
    retry_base_seconds: int,
    clock: ClockPort | None = None,
) -> PublishOutboxEventsUseCase:
    """Builds the outbox publication use case from shared presentation wiring."""
    return PublishOutboxEventsUseCase(
        repository=build_outbox_repository(session),
        publisher=publisher,
        clock=clock or UtcClock(),
        retry_base_seconds=retry_base_seconds,
    )


def build_idempotent_event_consumer(
    *,
    session: AsyncSession,
    handler: EventConsumerPort,
    clock: ClockPort | None = None,
) -> IdempotentEventConsumer:
    """Builds an inbox-backed idempotent consumer for future workers."""
    return IdempotentEventConsumer(
        inbox_repository=build_inbox_repository(session),
        handler=handler,
        clock=clock or UtcClock(),
    )


__all__ = [
    "build_idempotent_event_consumer",
    "build_inbox_repository",
    "build_integration_event_publisher",
    "build_outbox_repository",
    "build_publish_outbox_events_use_case",
]
