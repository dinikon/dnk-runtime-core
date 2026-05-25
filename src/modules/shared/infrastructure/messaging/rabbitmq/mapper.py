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
    arguments = ClassicQueueArgs(
        **{
            key: value
            for key, value in {
                "x-dead-letter-exchange": queue.dead_letter_exchange,
                "x-dead-letter-routing-key": queue.dead_letter_routing_key,
                "x-message-ttl": queue.message_ttl_ms,
                "x-max-length": queue.max_length,
            }.items()
            if value is not None
        }
    )

    return RabbitQueue(
        queue.name,
        durable=queue.durable,
        routing_key=queue.routing_key,
        arguments=arguments or None,
    )


__all__ = [
    "to_rabbit_exchange",
    "to_rabbit_queue",
]
