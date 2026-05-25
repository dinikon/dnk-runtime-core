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
    ensure_communication_topology,
    handle_outbound_message_job,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


class _BrokerPublisherStub:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, **kwargs):
        self.published.append(kwargs)


class _TopologyStub:
    def __init__(self) -> None:
        self.exchanges = []
        self.queues = []
        self.binds = []

    async def declare_exchange(self, exchange) -> None:
        self.exchanges.append(exchange)

    async def declare_queue(self, queue) -> None:
        self.queues.append(queue)

    async def bind_queue(self, *, queue, exchange, routing_key: str) -> None:
        self.binds.append((queue, exchange, routing_key))


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
        settings = CommunicationQueueSettings()
        broker_publisher = _BrokerPublisherStub()
        topology = _TopologyStub()
        publisher = RabbitMQOutboundMessagePublisher(
            broker_publisher=broker_publisher,
            settings=settings,
        )
        tenant_id = uuid4()
        outbound_message_id = uuid4()
        published_at = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)

        await ensure_communication_topology(topology, settings)
        await publisher.publish(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
            source="republisher",
            published_at=published_at,
        )

        self.assertEqual(len(topology.exchanges), 2)
        self.assertEqual(len(topology.queues), 2)
        self.assertEqual(len(topology.binds), 2)
        published = broker_publisher.published[0]
        message = published["message"]
        self.assertEqual(published["exchange"].name, settings.exchange_name)
        self.assertEqual(published["exchange"].type, "direct")
        self.assertEqual(published["routing_key"], settings.routing_key)
        self.assertEqual(message.payload["tenant_id"], str(tenant_id))
        self.assertEqual(
            message.payload["outbound_message_id"],
            str(outbound_message_id),
        )
        self.assertEqual(message.payload["source"], "republisher")
        self.assertTrue(message.persistent)
        self.assertEqual(message.message_id, str(outbound_message_id))
        self.assertEqual(message.message_type, "communication.outbound.send")

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

        self.assertIs(type(processed[0][0]), EntityIdVO)
        self.assertIs(type(processed[0][1]), OutboundMessageIdVO)
        self.assertEqual(processed[0][0].uuid, tenant_id)
        self.assertEqual(processed[0][1].uuid, outbound_message_id)
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
