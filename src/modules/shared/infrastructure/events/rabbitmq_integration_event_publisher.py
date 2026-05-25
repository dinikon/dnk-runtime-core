from __future__ import annotations

from collections.abc import Awaitable, Callable

from faststream.rabbit import (
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
)

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.application.messaging import BrokerMessage, MessagePublisherPort
from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.shared.infrastructure.messaging import RabbitMQMessagePublisher


def build_event_bus_exchange(settings: EventBusSettings) -> RabbitExchange:
    """Builds the durable integration event exchange."""
    return RabbitExchange(
        settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    )


async def ensure_event_bus_topology(
    broker: RabbitBroker,
    settings: EventBusSettings,
) -> None:
    """Declares broker topology required by the shared event bus."""
    await broker.declare_exchange(build_event_bus_exchange(settings))


class RabbitMQIntegrationEventPublisher:
    """Publishes integration events to RabbitMQ without leaking broker types upstream."""

    def __init__(
        self,
        *,
        message_publisher: MessagePublisherPort | None = None,
        exchange_name: str | None = None,
        setup_topology: Callable[[], Awaitable[None]] | None = None,
        broker: RabbitBroker | None = None,
        settings: EventBusSettings | None = None,
        manage_broker_lifecycle: bool = False,
    ) -> None:
        if message_publisher is None:
            if broker is None or settings is None:
                raise TypeError(
                    "Either message_publisher/exchange_name or broker/settings is required."
                )
            message_publisher = RabbitMQMessagePublisher(
                broker=broker,
                manage_broker_lifecycle=manage_broker_lifecycle,
            )
            exchange_name = settings.exchange_name
            if setup_topology is None:

                async def setup_topology() -> None:
                    await ensure_event_bus_topology(broker, settings)

        if exchange_name is None:
            raise TypeError("exchange_name is required.")
        self._message_publisher = message_publisher
        self._exchange_name = exchange_name
        self._setup_topology = setup_topology
        self._started = False

    @classmethod
    def from_settings(
        cls,
        settings: EventBusSettings,
        *,
        manage_broker_lifecycle: bool = False,
    ) -> "RabbitMQIntegrationEventPublisher":
        message_publisher = RabbitMQMessagePublisher.from_url(
            settings.rabbitmq_url,
            manage_broker_lifecycle=manage_broker_lifecycle,
        )

        async def setup_topology() -> None:
            await ensure_event_bus_topology(message_publisher.broker, settings)

        return cls(
            message_publisher=message_publisher,
            exchange_name=settings.exchange_name,
            setup_topology=setup_topology,
        )

    async def start(self) -> None:
        if self._started:
            return
        start = getattr(self._message_publisher, "start", None)
        if start is not None:
            await start()
        if self._setup_topology is not None:
            await self._setup_topology()
        self._started = True

    async def close(self) -> None:
        close = getattr(self._message_publisher, "close", None)
        if self._started and close is not None:
            await close()
        self._started = False

    async def __aenter__(self) -> "RabbitMQIntegrationEventPublisher":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def publish(self, event: IntegrationEvent) -> None:
        """Publishes one integration event with event type as routing key."""
        if not self._started:
            await self.start()
        await self._message_publisher.publish(
            exchange=self._exchange_name,
            routing_key=event.event_type,
            message=BrokerMessage(
                body=event.to_payload(),
                message_id=str(event.event_id),
            ),
            mandatory=True,
            persist=True,
            timestamp=event.occurred_at,
            message_type=event.event_type,
        )


__all__ = [
    "RabbitMQIntegrationEventPublisher",
    "build_event_bus_exchange",
    "ensure_event_bus_topology",
]
