from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager

from src.config.app_config import DnkConfig
from src.modules.shared.application.events.publish_outbox_events_command import (
    PublishOutboxEventsCommand,
)
from src.modules.shared.application.events.publish_outbox_result_dto import (
    PublishOutboxResultDTO,
)
from src.modules.shared.application.events.use_case import PublishOutboxEventsUseCase
from src.modules.shared.application.persistence import UnitOfWorkProtocol
from src.modules.shared.domain.time import ClockPort
from src.modules.shared.infrastructure.events.rabbitmq_integration_event_publisher import (
    RabbitMQIntegrationEventPublisher,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.shared.infrastructure.messaging.rabbitmq.broker_provider import (
    RabbitMQBrokerProvider,
)
from src.modules.shared.infrastructure.messaging.rabbitmq.broker_publisher import (
    RabbitMQBrokerPublisher,
)
from src.modules.shared.infrastructure.time import UtcClock

UnitOfWorkFactory = Callable[
    [],
    AbstractAsyncContextManager[UnitOfWorkProtocol],
]
PublishOnce = Callable[[], Awaitable[PublishOutboxResultDTO]]


def build_publish_once(
    *,
    config: DnkConfig,
    uow_factory: UnitOfWorkFactory,
    clock: ClockPort | None = None,
    broker_provider: RabbitMQBrokerProvider,
) -> PublishOnce:
    worker_clock = clock or UtcClock()

    async def publish_once() -> PublishOutboxResultDTO:
        async with uow_factory() as uow:
            repository = SqlAlchemyOutboxRepository(uow.session)
            broker_publisher = RabbitMQBrokerPublisher(broker_provider)
            event_publisher = RabbitMQIntegrationEventPublisher(
                broker_publisher=broker_publisher,
                settings=config.EVENT_BUS,
            )
            use_case = PublishOutboxEventsUseCase(
                repository=repository,
                publisher=event_publisher,
                clock=worker_clock,
                retry_base_seconds=config.EVENT_BUS.retry_base_seconds,
            )

            result = await use_case(
                PublishOutboxEventsCommand(
                    limit=config.EVENT_BUS.publish_limit,
                    max_attempts=config.EVENT_BUS.max_attempts,
                )
            )
            await uow.commit()
            return result

    return publish_once


__all__ = ["PublishOnce", "UnitOfWorkFactory", "build_publish_once"]
