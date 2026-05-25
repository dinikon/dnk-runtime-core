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
        arguments=_to_classic_queue_args(queue),
    )


def _to_classic_queue_args(queue: BrokerQueue) -> ClassicQueueArgs | None:
    if queue.arguments is None:
        return None

    args: ClassicQueueArgs = {}

    if queue.arguments.dead_letter_exchange is not None:
        args["x-dead-letter-exchange"] = queue.arguments.dead_letter_exchange

    if queue.arguments.dead_letter_routing_key is not None:
        args["x-dead-letter-routing-key"] = queue.arguments.dead_letter_routing_key

    if queue.arguments.message_ttl_ms is not None:
        args["x-message-ttl"] = queue.arguments.message_ttl_ms

    if queue.arguments.max_length is not None:
        args["x-max-length"] = queue.arguments.max_length

    return args or None


__all__ = [
    "to_rabbit_exchange",
    "to_rabbit_queue",
]
