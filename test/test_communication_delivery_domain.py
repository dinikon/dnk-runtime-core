from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.modules.communication.domain.delivery import (
    AttemptStatus,
    DeliveryAttemptIdVO,
    DeliveryEventIdVO,
    DeliveryEventType,
    DeliveryService,
    ExternalMessageId,
    InvalidExternalMessageIdError,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.domain.provider_connection import ProviderConnectionIdVO
from src.modules.shared import EntityIdVO


class _ClockStub:
    def now(self):
        return datetime(2026, 5, 14, 12, 0, tzinfo=UTC)


class _DeliveryRepositoryStub:
    def __init__(self) -> None:
        self.attempt = None
        self.event = None
        self.updated_outbound = None

    async def next_attempt_no(self, **_kwargs):
        return 2

    async def save_delivery_attempt(self, *, tenant_id, attempt):
        self.attempt = attempt
        return attempt

    async def get_delivery_attempt(self, **_kwargs):
        return self.attempt

    async def add_delivery_event(self, *, tenant_id, event):
        self.event = event
        return event

    async def update_outbound_status_from_event(self, **kwargs):
        self.updated_outbound = kwargs


class CommunicationDeliveryDomainTests(unittest.IsolatedAsyncioTestCase):
    def test_external_message_id_rejects_empty_value(self) -> None:
        with self.assertRaises(InvalidExternalMessageIdError):
            ExternalMessageId("   ")

    async def test_service_starts_and_completes_delivery_attempt(self) -> None:
        repository = _DeliveryRepositoryStub()
        service = DeliveryService(repository=repository, clock=_ClockStub())
        tenant_id = EntityIdVO.from_value(uuid4())
        attempt_id = DeliveryAttemptIdVO.from_value(uuid4())

        attempt = await service.start_attempt(
            tenant_id=tenant_id,
            delivery_attempt_id=attempt_id,
            outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
            request_payload={"message": "hello"},
        )
        completed = await service.complete_attempt(
            tenant_id=tenant_id,
            delivery_attempt_id=attempt_id,
            response_payload={"ok": True},
            http_status_code=200,
            external_message_id=" ext-1 ",
            finished_at=datetime(2026, 5, 14, 12, 1, tzinfo=UTC),
        )

        self.assertEqual(attempt.attempt_no, 2)
        self.assertEqual(completed.status, AttemptStatus.SUCCESS.value)
        self.assertEqual(completed.external_message_id, "ext-1")

    async def test_service_records_webhook_event_and_updates_outbound(self) -> None:
        repository = _DeliveryRepositoryStub()
        service = DeliveryService(repository=repository, clock=_ClockStub())
        tenant_id = EntityIdVO.from_value(uuid4())
        outbound = SimpleNamespace(
            outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
        )

        event = await service.record_webhook_event(
            tenant_id=tenant_id,
            delivery_event_id=DeliveryEventIdVO.from_value(uuid4()),
            outbound=outbound,
            external_message_id="ext-1",
            external_status="Delivered",
            internal_status=DeliveryEventType.DELIVERED.value,
            event_at=None,
            raw_payload={"message_id": "ext-1"},
        )

        self.assertEqual(event.external_message_id, "ext-1")
        self.assertEqual(event.event_type, DeliveryEventType.DELIVERED.value)
        self.assertEqual(
            repository.updated_outbound["outbound_message_id"],
            outbound.outbound_message_id,
        )


__all__ = ["CommunicationDeliveryDomainTests"]
