from typing import cast

from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import ClassicQueueArgs

from src.modules.shared.application.messaging import BrokerExchange, BrokerQueue


def to_rabbit_exchange(exchange: BrokerExchange) -> RabbitExchange:
    return RabbitExchange(
        exchange.name,
        type={
            "direct": ExchangeType.DIRECT,
            "topic": ExchangeType.TOPIC,
            "fanout": ExchangeType.FANOUT,
            "headers": ExchangeType.HEADERS,
        }[exchange.type],
        durable=exchange.durable,
    )


def to_rabbit_queue(queue: BrokerQueue) -> RabbitQueue:
    return RabbitQueue(
        queue.name,
        durable=queue.durable,
        routing_key=queue.routing_key,
        arguments=cast(ClassicQueueArgs, dict(queue.arguments)) or None,
    )


__all__ = [
    "to_rabbit_exchange",
    "to_rabbit_queue",
]
