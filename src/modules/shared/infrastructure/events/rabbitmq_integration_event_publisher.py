from __future__ import annotations

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.application.events import EventPublisherPort
from src.modules.shared.application.messaging import (
    BrokerExchange,
    BrokerMessage,
    BrokerPublisherPort,
    BrokerTopologyPort,
)
from src.modules.shared.domain.events.integration_event import IntegrationEvent


def build_event_bus_exchange(settings: EventBusSettings) -> BrokerExchange:
    return BrokerExchange(
        name=settings.exchange_name,
        type="topic",
        durable=True,
    )


async def ensure_event_bus_topology(
    topology: BrokerTopologyPort,
    settings: EventBusSettings,
) -> None:
    await topology.declare_exchange(build_event_bus_exchange(settings))


class RabbitMQIntegrationEventPublisher(EventPublisherPort):
    def __init__(
        self,
        *,
        broker_publisher: BrokerPublisherPort,
        settings: EventBusSettings,
    ) -> None:
        self._broker_publisher = broker_publisher
        self._settings = settings

    async def publish(self, event: IntegrationEvent) -> None:
        await self._broker_publisher.publish(
            exchange=build_event_bus_exchange(self._settings),
            routing_key=event.event_type,
            message=BrokerMessage(
                payload=event.to_payload(),
                message_id=str(event.event_id),
                message_type=event.event_type,
                timestamp=event.occurred_at,
                headers={
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                    "event_version": str(event.event_version),
                    "tenant_id": str(event.tenant_id),
                    "aggregate_type": event.aggregate_type,
                    "aggregate_id": str(event.aggregate_id),
                },
            ),
        )


__all__ = [
    "RabbitMQIntegrationEventPublisher",
    "build_event_bus_exchange",
    "ensure_event_bus_topology",
]
