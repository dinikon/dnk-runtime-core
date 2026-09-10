from __future__ import annotations

from src.modules.shared.application.messaging import (
    BrokerExchange,
    BrokerQueue,
    BrokerTopologyPort,
)
from src.modules.shared.infrastructure.messaging.rabbitmq.broker_provider import (
    RabbitMQBrokerProvider,
)
from src.modules.shared.infrastructure.messaging.rabbitmq.mapper import (
    to_rabbit_exchange,
    to_rabbit_queue,
)


class RabbitMQTopologyManager(BrokerTopologyPort):
    def __init__(self, broker_provider: RabbitMQBrokerProvider) -> None:
        self._broker_provider = broker_provider

    async def declare_exchange(self, exchange: BrokerExchange) -> None:
        await self._broker_provider.start()
        await self._broker_provider.broker.declare_exchange(
            to_rabbit_exchange(exchange)
        )

    async def declare_queue(self, queue: BrokerQueue) -> None:
        await self._broker_provider.start()
        await self._broker_provider.broker.declare_queue(to_rabbit_queue(queue))

    async def bind_queue(
        self,
        *,
        queue: BrokerQueue,
        exchange: BrokerExchange,
        routing_key: str,
    ) -> None:
        await self._broker_provider.start()
        rabbit_exchange = await self._broker_provider.broker.declare_exchange(
            to_rabbit_exchange(exchange)
        )
        rabbit_queue = await self._broker_provider.broker.declare_queue(
            to_rabbit_queue(queue)
        )
        await rabbit_queue.bind(rabbit_exchange, routing_key=routing_key)


__all__ = ["RabbitMQTopologyManager"]
