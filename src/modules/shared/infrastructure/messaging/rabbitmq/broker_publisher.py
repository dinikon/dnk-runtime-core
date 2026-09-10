from __future__ import annotations

from src.modules.shared.application.messaging import (
    BrokerExchange,
    BrokerMessage,
    BrokerPublisherPort,
)
from src.modules.shared.infrastructure.messaging.rabbitmq.broker_provider import (
    RabbitMQBrokerProvider,
)
from src.modules.shared.infrastructure.messaging.rabbitmq.mapper import (
    to_rabbit_exchange,
)


class RabbitMQBrokerPublisher(BrokerPublisherPort):
    def __init__(self, broker_provider: RabbitMQBrokerProvider) -> None:
        self._broker_provider = broker_provider

    async def publish(
        self,
        *,
        exchange: BrokerExchange,
        routing_key: str,
        message: BrokerMessage,
        mandatory: bool = True,
    ) -> None:
        await self._broker_provider.start()

        await self._broker_provider.broker.publish(
            dict(message.payload),
            exchange=to_rabbit_exchange(exchange),
            routing_key=routing_key,
            mandatory=mandatory,
            persist=message.persistent,
            message_id=message.message_id,
            correlation_id=message.correlation_id,
            message_type=message.message_type,
            timestamp=message.timestamp,
            headers=dict(message.headers),
        )


__all__ = ["RabbitMQBrokerPublisher"]
