from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from src.config.infrastructure.communication_queue_config import (
    CommunicationQueueSettings,
)
from src.modules.communication.infrastructure.rabbitmq import (
    RabbitMQOutboundMessagePublisher,
    handle_outbound_message_job,
)


class _DeclaredQueueStub:
    def __init__(self) -> None:
        self.binds = []

    async def bind(self, exchange, *, routing_key: str) -> None:
        self.binds.append((exchange, routing_key))


class _RabbitBrokerStub:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.exchanges = []
        self.queues = []
        self.published = []
        self.declared_queues = []

    async def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        self.closed = True

    async def declare_exchange(self, exchange):
        self.exchanges.append(exchange)
        return exchange

    async def declare_queue(self, queue):
        self.queues.append(queue)
        declared = _DeclaredQueueStub()
        self.declared_queues.append(declared)
        return declared

    async def publish(self, message, **kwargs):
        self.published.append((message, kwargs))


class _MessageStub:
    def __init__(self) -> None:
        self.acked = False
        self.rejected = False
        self.nacked = False
        self.requeue = None

    async def ack(self) -> None:
        self.acked = True

    async def reject(self, *, requeue: bool = False) -> None:
        self.rejected = True
        self.requeue = requeue

    async def nack(self, *, requeue: bool = True) -> None:
        self.nacked = True
        self.requeue = requeue


class CommunicationQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_rabbitmq_publisher_declares_topology_and_publishes_persistent_job(
        self,
    ) -> None:
        broker = _RabbitBrokerStub()
        settings = CommunicationQueueSettings()
        publisher = RabbitMQOutboundMessagePublisher(
            broker=broker,
            settings=settings,
            manage_broker_lifecycle=True,
        )
        tenant_id = uuid4()
        outbound_message_id = uuid4()
        published_at = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)

        async with publisher:
            await publisher.publish(
                tenant_id=tenant_id,
                outbound_message_id=outbound_message_id,
                source="republisher",
                published_at=published_at,
            )

        self.assertTrue(broker.started)
        self.assertTrue(broker.closed)
        self.assertEqual(len(broker.exchanges), 2)
        self.assertEqual(len(broker.queues), 2)
        payload, kwargs = broker.published[0]
        self.assertEqual(payload["tenant_id"], str(tenant_id))
        self.assertEqual(payload["outbound_message_id"], str(outbound_message_id))
        self.assertEqual(payload["source"], "republisher")
        self.assertTrue(kwargs["persist"])
        self.assertTrue(kwargs["mandatory"])
        self.assertEqual(kwargs["message_id"], str(outbound_message_id))

    async def test_consumer_acknowledges_valid_job_after_processor_success(
        self,
    ) -> None:
        outbound_message_id = uuid4()
        tenant_id = uuid4()
        message = _MessageStub()
        processed = []

        async def processor(command):
            processed.append((command.tenant_id, command.outbound_message_id))
            return SimpleNamespace()

        await handle_outbound_message_job(
            payload={
                "tenant_id": str(tenant_id),
                "outbound_message_id": str(outbound_message_id),
                "published_at": "2026-05-11T12:00:00+00:00",
                "source": "republisher",
            },
            message=message,
            processor=processor,
        )

        self.assertEqual(processed, [(tenant_id, outbound_message_id)])
        self.assertTrue(message.acked)
        self.assertFalse(message.rejected)
        self.assertFalse(message.nacked)

    async def test_consumer_rejects_invalid_job_without_requeue(self) -> None:
        message = _MessageStub()

        async def processor(_command):
            raise AssertionError("invalid payload must not reach processor")

        await handle_outbound_message_job(
            payload={"outbound_message_id": "not-a-uuid"},
            message=message,
            processor=processor,
        )

        self.assertTrue(message.rejected)
        self.assertFalse(message.requeue)
        self.assertFalse(message.acked)
        self.assertFalse(message.nacked)

    async def test_consumer_nacks_unexpected_processing_error(self) -> None:
        message = _MessageStub()

        async def processor(_command):
            raise RuntimeError("db is down")

        await handle_outbound_message_job(
            payload={
                "tenant_id": str(UUID(int=1)),
                "outbound_message_id": str(UUID(int=1)),
                "published_at": "2026-05-11T12:00:00+00:00",
                "source": "republisher",
            },
            message=message,
            processor=processor,
        )

        self.assertTrue(message.nacked)
        self.assertTrue(message.requeue)
        self.assertFalse(message.acked)
        self.assertFalse(message.rejected)


__all__ = ["CommunicationQueueTests"]
