from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.modules.shared.application.messaging import BrokerMessage
from src.modules.shared.infrastructure.messaging import RabbitMQMessagePublisher


class _RabbitBrokerStub:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.start_count = 0
        self.published = []

    async def start(self) -> None:
        self.started = True
        self.start_count += 1

    async def close(self) -> None:
        self.closed = True

    async def publish(self, message, **kwargs) -> None:
        self.published.append((message, kwargs))


class SharedMessagingTests(unittest.IsolatedAsyncioTestCase):
    async def test_rabbitmq_message_publisher_manages_broker_lifecycle(self) -> None:
        broker = _RabbitBrokerStub()
        publisher = RabbitMQMessagePublisher(
            broker=broker,
            manage_broker_lifecycle=True,
        )

        async with publisher:
            self.assertTrue(broker.started)

        self.assertTrue(broker.closed)

    async def test_rabbitmq_message_publisher_publishes_body_and_metadata(
        self,
    ) -> None:
        broker = _RabbitBrokerStub()
        publisher = RabbitMQMessagePublisher(
            broker=broker,
            manage_broker_lifecycle=False,
        )
        timestamp = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)

        await publisher.publish(
            exchange="example.exchange",
            routing_key="example.key",
            message=BrokerMessage(
                body={"hello": "world"},
                headers={"message_kind": "example"},
                message_id="message-id",
                correlation_id="correlation-id",
            ),
            timestamp=timestamp,
            message_type="example.message",
        )

        payload, kwargs = broker.published[0]
        self.assertEqual(payload, {"hello": "world"})
        self.assertEqual(kwargs["exchange"], "example.exchange")
        self.assertEqual(kwargs["routing_key"], "example.key")
        self.assertEqual(kwargs["headers"], {"message_kind": "example"})
        self.assertEqual(kwargs["message_id"], "message-id")
        self.assertEqual(kwargs["correlation_id"], "correlation-id")
        self.assertEqual(kwargs["timestamp"], timestamp)
        self.assertEqual(kwargs["message_type"], "example.message")
        self.assertTrue(kwargs["mandatory"])
        self.assertTrue(kwargs["persist"])

    async def test_rabbitmq_message_publisher_lazy_starts_before_publish(self) -> None:
        broker = _RabbitBrokerStub()
        publisher = RabbitMQMessagePublisher(
            broker=broker,
            manage_broker_lifecycle=False,
        )

        await publisher.publish(
            exchange="example.exchange",
            routing_key="example.key",
            message=BrokerMessage(body={}),
        )

        self.assertTrue(broker.started)
        self.assertEqual(broker.start_count, 1)


__all__ = ["SharedMessagingTests"]
