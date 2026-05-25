from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.application.events import (
    HandleIntegrationEventCommand,
    IdempotentEventConsumer,
    PublishOutboxEventsCommand,
    PublishOutboxEventsUseCase,
)
from src.modules.shared.infrastructure.events import RabbitMQIntegrationEventPublisher
from src.modules.shared.infrastructure.events import ensure_event_bus_topology
from src.modules.shared.domain.events import IntegrationEvent, OutboxEvent


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _OutboxRepositoryStub:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self.events = events
        self.claim_args = None
        self.published = []
        self.failed = []

    async def claim_due_events(self, *, limit: int, now: datetime):
        self.claim_args = (limit, now)
        return list(self.events)

    async def mark_published(self, *, event_id, published_at: datetime) -> None:
        self.published.append((event_id, published_at))

    async def mark_publish_failed(
        self,
        *,
        event_id,
        error: str,
        next_attempt_at: datetime | None,
    ) -> None:
        self.failed.append((event_id, error, next_attempt_at))


class _PublisherStub:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.published = []

    async def publish(self, event: IntegrationEvent) -> None:
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.published.append(event)


class _InboxRepositoryStub:
    def __init__(self, *, first_delivery: bool) -> None:
        self.first_delivery = first_delivery
        self.received = []
        self.consumed = []
        self.failed = []

    async def record_received(
        self,
        *,
        source: str,
        message_id: str,
        event: IntegrationEvent,
        received_at: datetime,
    ) -> bool:
        self.received.append((source, message_id, event, received_at))
        return self.first_delivery

    async def mark_consumed(
        self,
        *,
        tenant_id,
        source: str,
        message_id: str,
        consumed_at: datetime,
    ) -> None:
        self.consumed.append((tenant_id, source, message_id, consumed_at))

    async def mark_failed(
        self,
        *,
        tenant_id,
        source: str,
        message_id: str,
        error: str,
    ) -> None:
        self.failed.append((tenant_id, source, message_id, error))


class _HandlerStub:
    def __init__(self) -> None:
        self.events = []

    async def handle(self, event: IntegrationEvent) -> None:
        self.events.append(event)


class _BrokerPublisherStub:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, **kwargs) -> None:
        self.published.append(kwargs)


class _TopologyStub:
    def __init__(self) -> None:
        self.exchanges = []

    async def declare_exchange(self, exchange) -> None:
        self.exchanges.append(exchange)

    async def declare_queue(self, queue) -> None:
        raise AssertionError("event bus topology does not declare queues")

    async def bind_queue(self, **_kwargs) -> None:
        raise AssertionError("event bus topology does not bind queues")


class SharedEventsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        self.event = IntegrationEvent(
            event_id=uuid4(),
            tenant_id=uuid4(),
            event_type="crm.contact.created",
            event_version=1,
            aggregate_type="contact",
            aggregate_id=uuid4(),
            payload={"name": "Ada"},
            occurred_at=self.now,
        )

    def _outbox_event(self, *, publish_attempts: int = 1) -> OutboxEvent:
        return OutboxEvent(
            id=self.event.event_id,
            tenant_id=self.event.tenant_id,
            event_type=self.event.event_type,
            event_version=self.event.event_version,
            aggregate_type=self.event.aggregate_type,
            aggregate_id=self.event.aggregate_id,
            payload=dict(self.event.payload),
            occurred_at=self.event.occurred_at,
            published_at=None,
            publish_attempts=publish_attempts,
            status="publishing",
            next_attempt_at=None,
            last_error=None,
        )

    def test_integration_event_serializes_round_trip_payload(self) -> None:
        payload = self.event.to_payload()

        result = IntegrationEvent.from_payload(payload)

        self.assertEqual(result, self.event)
        self.assertEqual(payload["event_id"], str(self.event.event_id))
        self.assertEqual(payload["tenant_id"], str(self.event.tenant_id))
        self.assertEqual(payload["aggregate_id"], str(self.event.aggregate_id))
        self.assertEqual(payload["occurred_at"], self.now.isoformat())

    async def test_publish_outbox_marks_successful_event_published(self) -> None:
        repository = _OutboxRepositoryStub([self._outbox_event()])
        publisher = _PublisherStub()
        use_case = PublishOutboxEventsUseCase(
            repository=repository,
            publisher=publisher,
            clock=_ClockStub(self.now),
            retry_base_seconds=30,
        )

        result = await use_case(PublishOutboxEventsCommand(limit=10, max_attempts=5))

        self.assertEqual(result.scanned, 1)
        self.assertEqual(result.published, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(repository.claim_args, (10, self.now))
        self.assertEqual(publisher.published, [self.event])
        self.assertEqual(repository.published, [(self.event.event_id, self.now)])

    async def test_publish_outbox_schedules_retry_for_failed_event(self) -> None:
        repository = _OutboxRepositoryStub([self._outbox_event(publish_attempts=2)])
        publisher = _PublisherStub(fail=True)
        use_case = PublishOutboxEventsUseCase(
            repository=repository,
            publisher=publisher,
            clock=_ClockStub(self.now),
            retry_base_seconds=30,
        )

        result = await use_case(PublishOutboxEventsCommand(limit=10, max_attempts=5))

        self.assertEqual(result.failed, 1)
        self.assertEqual(
            repository.failed,
            [
                (
                    self.event.event_id,
                    "broker unavailable",
                    self.now + timedelta(seconds=60),
                )
            ],
        )

    async def test_publish_outbox_fails_event_after_max_attempts(self) -> None:
        repository = _OutboxRepositoryStub([self._outbox_event(publish_attempts=5)])
        publisher = _PublisherStub(fail=True)
        use_case = PublishOutboxEventsUseCase(
            repository=repository,
            publisher=publisher,
            clock=_ClockStub(self.now),
            retry_base_seconds=30,
        )

        result = await use_case(PublishOutboxEventsCommand(limit=10, max_attempts=5))

        self.assertEqual(result.failed, 1)
        self.assertEqual(
            repository.failed,
            [(self.event.event_id, "broker unavailable", None)],
        )

    async def test_idempotent_consumer_runs_handler_for_first_delivery(self) -> None:
        inbox = _InboxRepositoryStub(first_delivery=True)
        handler = _HandlerStub()
        consumer = IdempotentEventConsumer(
            inbox_repository=inbox,
            handler=handler,
            clock=_ClockStub(self.now),
        )

        result = await consumer(
            HandleIntegrationEventCommand(
                source="rabbitmq",
                message_id=str(self.event.event_id),
            ),
            self.event,
        )

        self.assertTrue(result.consumed)
        self.assertFalse(result.duplicate)
        self.assertEqual(handler.events, [self.event])
        self.assertEqual(len(inbox.consumed), 1)
        self.assertEqual(inbox.consumed[0][0], self.event.tenant_id)

    async def test_idempotent_consumer_skips_duplicate_delivery(self) -> None:
        inbox = _InboxRepositoryStub(first_delivery=False)
        handler = _HandlerStub()
        consumer = IdempotentEventConsumer(
            inbox_repository=inbox,
            handler=handler,
            clock=_ClockStub(self.now),
        )

        result = await consumer(
            HandleIntegrationEventCommand(
                source="rabbitmq",
                message_id=str(self.event.event_id),
            ),
            self.event,
        )

        self.assertFalse(result.consumed)
        self.assertTrue(result.duplicate)
        self.assertEqual(handler.events, [])
        self.assertEqual(inbox.consumed, [])

    async def test_rabbitmq_publisher_declares_exchange_and_publishes_event(
        self,
    ) -> None:
        settings = EventBusSettings()
        broker_publisher = _BrokerPublisherStub()
        topology = _TopologyStub()
        publisher = RabbitMQIntegrationEventPublisher(
            broker_publisher=broker_publisher,
            settings=settings,
        )

        await ensure_event_bus_topology(topology, settings)
        await publisher.publish(self.event)

        self.assertEqual(len(topology.exchanges), 1)
        self.assertEqual(topology.exchanges[0].name, settings.exchange_name)
        published = broker_publisher.published[0]
        self.assertEqual(published["exchange"].name, settings.exchange_name)
        self.assertEqual(published["exchange"].type, "topic")
        self.assertEqual(published["routing_key"], self.event.event_type)
        self.assertEqual(published["message"].payload, self.event.to_payload())
        self.assertEqual(published["message"].message_id, str(self.event.event_id))
        self.assertEqual(published["message"].message_type, self.event.event_type)
        self.assertEqual(published["message"].timestamp, self.event.occurred_at)
        self.assertEqual(
            published["message"].headers["event_id"],
            str(self.event.event_id),
        )


__all__ = ["SharedEventsTests"]
