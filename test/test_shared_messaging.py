from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.modules.shared.application.messaging import (
    BrokerExchange,
    BrokerMessage,
    BrokerQueue,
)
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerPublisher,
    RabbitMQTopologyManager,
)


class _DeclaredQueueStub:
    def __init__(self) -> None:
        self.binds = []

    async def bind(self, exchange, *, routing_key: str) -> None:
        self.binds.append((exchange, routing_key))


class _RabbitBrokerStub:

    def __init__(self) -> None:
        self.published = []
        self.exchanges = []
        self.queues = []
        self.declared_queues = []

    async def publish(self, message, **kwargs) -> None:
        self.published.append((message, kwargs))

    async def declare_exchange(self, exchange):
        self.exchanges.append(exchange)
        return exchange

    async def declare_queue(self, queue):
        self.queues.append(queue)
        declared = _DeclaredQueueStub()
        self.declared_queues.append(declared)
        return declared


class _BrokerProviderStub:
    def __init__(self) -> None:
        self.started = False
        self.start_count = 0
        self.broker = _RabbitBrokerStub()

    async def start(self) -> None:
        self.started = True
        self.start_count += 1


class SharedMessagingTests(unittest.IsolatedAsyncioTestCase):

    def test_broker_message_defaults_are_broker_neutral(self) -> None:
        message = BrokerMessage(payload={"hello": "world"})

        self.assertEqual(message.payload, {"hello": "world"})
        self.assertEqual(message.headers, {})
        self.assertIsNone(message.message_id)
        self.assertTrue(message.persistent)

    def test_broker_exchange_and_queue_describe_topology(self) -> None:
        exchange = BrokerExchange(name="example.exchange", type="topic")
        queue = BrokerQueue(
            name="example.queue",
            routing_key="example.*",
            arguments={"x-dead-letter-exchange": "example.dlx"},
        )

        self.assertEqual(exchange.type, "topic")
        self.assertTrue(exchange.durable)
        self.assertEqual(queue.routing_key, "example.*")
        self.assertEqual(
            queue.arguments,
            {"x-dead-letter-exchange": "example.dlx"},
        )

    async def test_rabbitmq_broker_publisher_publishes_payload_and_metadata(
        self,
    ) -> None:
        provider = _BrokerProviderStub()
        publisher = RabbitMQBrokerPublisher(provider)
        timestamp = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)

        await publisher.publish(
            exchange=BrokerExchange(name="example.exchange", type="topic"),
            routing_key="example.key",
            message=BrokerMessage(
                payload={"hello": "world"},
                headers={"message_kind": "example"},
                message_id="message-id",
                correlation_id="correlation-id",
                message_type="example.message",
                timestamp=timestamp,
            ),
        )

        payload, kwargs = provider.broker.published[0]
        self.assertTrue(provider.started)
        self.assertEqual(provider.start_count, 1)
        self.assertEqual(payload, {"hello": "world"})
        self.assertEqual(kwargs["exchange"].name, "example.exchange")
        self.assertEqual(kwargs["routing_key"], "example.key")
        self.assertEqual(kwargs["headers"], {"message_kind": "example"})
        self.assertEqual(kwargs["message_id"], "message-id")
        self.assertEqual(kwargs["correlation_id"], "correlation-id")
        self.assertEqual(kwargs["timestamp"], timestamp)
        self.assertEqual(kwargs["message_type"], "example.message")
        self.assertTrue(kwargs["mandatory"])
        self.assertTrue(kwargs["persist"])

    async def test_rabbitmq_topology_manager_declares_and_binds(self) -> None:
        provider = _BrokerProviderStub()
        topology = RabbitMQTopologyManager(provider)
        exchange = BrokerExchange(name="example.exchange", type="direct")
        queue = BrokerQueue(name="example.queue", routing_key="example.key")

        await topology.bind_queue(
            queue=queue,
            exchange=exchange,
            routing_key="example.key",
        )

        self.assertTrue(provider.started)
        self.assertEqual(provider.broker.exchanges[0].name, "example.exchange")
        self.assertEqual(provider.broker.queues[0].name, "example.queue")
        self.assertEqual(
            provider.broker.declared_queues[0].binds[0][1],
            "example.key",
        )


__all__ = ["SharedMessagingTests"]
