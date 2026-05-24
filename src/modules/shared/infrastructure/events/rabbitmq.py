from __future__ import annotations

from faststream.rabbit import (
    Channel,
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
)

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.kernel.events import IntegrationEvent


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
        broker: RabbitBroker,
        settings: EventBusSettings,
        manage_broker_lifecycle: bool = False,
    ) -> None:
        self._broker = broker
        self._settings = settings
        self._manage_broker_lifecycle = manage_broker_lifecycle
        self._started = False

    @classmethod
    def from_settings(
        cls,
        settings: EventBusSettings,
        *,
        manage_broker_lifecycle: bool = False,
    ) -> "RabbitMQIntegrationEventPublisher":
        broker = RabbitBroker(
            settings.rabbitmq_url,
            default_channel=Channel(publisher_confirms=True),
        )
        return cls(
            broker=broker,
            settings=settings,
            manage_broker_lifecycle=manage_broker_lifecycle,
        )

    async def start(self) -> None:
        if self._started:
            return
        await self._broker.start()
        await ensure_event_bus_topology(self._broker, self._settings)
        self._started = True

    async def close(self) -> None:
        if self._started and self._manage_broker_lifecycle:
            await self._broker.close()
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
        await self._broker.publish(
            event.to_payload(),
            exchange=build_event_bus_exchange(self._settings),
            routing_key=event.event_type,
            mandatory=True,
            persist=True,
            message_id=str(event.event_id),
            timestamp=event.occurred_at,
            message_type=event.event_type,
        )


__all__ = [
    "RabbitMQIntegrationEventPublisher",
    "build_event_bus_exchange",
    "ensure_event_bus_topology",
]
