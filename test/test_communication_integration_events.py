from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from src.modules.communication.application.outbound_message.integration_events import (
    DELIVERY_STATUS_CHANGED_EVENT,
    OUTBOUND_MESSAGE_DELIVERED_EVENT,
    OUTBOUND_MESSAGE_FAILED_EVENT,
    OUTBOUND_MESSAGE_SENT_EVENT,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    OutboundMessage,
    OutboundMessageIdVO,
    OutboundMessageStatus,
)
from src.modules.communication.domain.provider_connection import ProviderConnectionIdVO
from src.modules.communication.infrastructure.delivery import (
    DeliveryRuntimeRepository,
    OutboundProcessingRuntimeRepository,
)
from src.modules.shared import EntityIdVO


class _OutboxRepositoryStub:
    def __init__(self) -> None:
        self.events = []

    async def add(self, event) -> None:
        self.events.append(event)


class _OutboundRepositoryStub:
    def __init__(self, outbound: OutboundMessage) -> None:
        self.outbound = outbound

    async def complete_outbound_processing(self, **_kwargs) -> bool:
        return True

    async def fail_outbound_processing(self, **_kwargs) -> bool:
        return True

    async def get_outbound_by_id(self, _tenant_id, _outbound_message_id):
        return self.outbound


class _DeliveryServiceStub:
    async def complete_attempt(self, **_kwargs):
        return None

    async def fail_attempt(self, **_kwargs):
        return None


class _RuntimeQueryGatewayStub:
    def __init__(self, row: dict) -> None:
        self.row = row

    async def get_by_id(self, *, descriptor, object_id):
        return dict(self.row)


class _RuntimeCommandGatewayStub:
    def __init__(self) -> None:
        self.updates = []

    async def update(self, *, descriptor, object_id, patch):
        self.updates.append((descriptor, object_id, patch))


class _RuntimeObjectResolverStub:
    async def resolve(self, *, tenant_id, object_name):
        return SimpleNamespace(tenant_id=tenant_id, object_name=object_name)


class CommunicationIntegrationEventsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        self.tenant_id = EntityIdVO.from_value(uuid4())
        self.outbound_id = OutboundMessageIdVO.from_value(uuid4())
        self.request_id = CommunicationRequestIdVO.from_value(uuid4())
        self.provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        self.outbound = OutboundMessage(
            outbound_message_id=self.outbound_id,
            tenant_id=self.tenant_id,
            communication_request_id=self.request_id,
            provider_connection_id=self.provider_connection_id,
            channel_code="sms",
            priority=100,
            recipient_identifier_type="PHONE",
            recipient_address="+15551234567",
            recipient_snapshot={"source_kind": "RAW_VALUE"},
            rendered_payload={},
            provider_request_payload={},
            external_message_id="external-1",
            external_status="accepted",
            internal_status=OutboundMessageStatus.SENDING.value,
            error_code=None,
            error_message=None,
            queued_at=self.now,
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            processing_token=EntityIdVO.from_value(uuid4()),
            processing_started_at=self.now,
            processing_deadline_at=self.now + timedelta(seconds=300),
            next_attempt_at=None,
            queue_published_at=self.now,
            queue_publish_count=1,
            created_at=self.now,
            updated_at=self.now,
        )

    async def test_successful_processing_writes_sent_outbox_event(self) -> None:
        outbox = _OutboxRepositoryStub()
        repository = OutboundProcessingRuntimeRepository(
            outbound_repository=_OutboundRepositoryStub(self.outbound),
            delivery_service=_DeliveryServiceStub(),
            outbox_repository=outbox,
        )

        await repository.complete_outbound_processing(
            tenant_id=self.tenant_id,
            outbound_message_id=self.outbound_id,
            processing_token=self.outbound.processing_token,
            delivery_attempt_id=None,
            rendered_payload={},
            provider_request_payload={},
            response_payload={},
            http_status_code=200,
            external_message_id="external-1",
            external_status="accepted",
            internal_status=OutboundMessageStatus.SENT.value,
            finished_at=self.now,
        )

        self.assertEqual(len(outbox.events), 1)
        event = outbox.events[0]
        self.assertEqual(event.event_type, OUTBOUND_MESSAGE_SENT_EVENT)
        self.assertEqual(event.aggregate_id, self.outbound_id.uuid)
        self.assertEqual(event.payload["internal_status"], "SENT")

    async def test_terminal_processing_failure_writes_failed_outbox_event(
        self,
    ) -> None:
        outbox = _OutboxRepositoryStub()
        repository = OutboundProcessingRuntimeRepository(
            outbound_repository=_OutboundRepositoryStub(self.outbound),
            delivery_service=_DeliveryServiceStub(),
            outbox_repository=outbox,
        )

        await repository.fail_outbound_processing(
            tenant_id=self.tenant_id,
            outbound_message_id=self.outbound_id,
            processing_token=self.outbound.processing_token,
            delivery_attempt_id=None,
            error_code="PROVIDER_FAILED",
            error_message="Provider send failed.",
            finished_at=self.now,
            external_message_id="external-1",
            external_status="failed",
            retry_at=None,
        )

        self.assertEqual(len(outbox.events), 1)
        self.assertEqual(outbox.events[0].event_type, OUTBOUND_MESSAGE_FAILED_EVENT)

    async def test_retryable_processing_failure_does_not_write_failed_event(
        self,
    ) -> None:
        outbox = _OutboxRepositoryStub()
        repository = OutboundProcessingRuntimeRepository(
            outbound_repository=_OutboundRepositoryStub(self.outbound),
            delivery_service=_DeliveryServiceStub(),
            outbox_repository=outbox,
        )

        await repository.fail_outbound_processing(
            tenant_id=self.tenant_id,
            outbound_message_id=self.outbound_id,
            processing_token=self.outbound.processing_token,
            delivery_attempt_id=None,
            error_code="PROVIDER_RATE_LIMIT",
            error_message="Rate limited.",
            finished_at=self.now,
            retry_at=self.now + timedelta(seconds=30),
        )

        self.assertEqual(outbox.events, [])

    async def test_webhook_delivered_update_writes_changed_and_delivered_events(
        self,
    ) -> None:
        outbox = _OutboxRepositoryStub()
        command_gateway = _RuntimeCommandGatewayStub()
        repository = DeliveryRuntimeRepository(
            runtime_object_resolver=_RuntimeObjectResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=_RuntimeQueryGatewayStub(self._outbound_row()),
            outbox_repository=outbox,
        )

        await repository.update_outbound_status_from_event(
            tenant_id=self.tenant_id,
            outbound_message_id=self.outbound_id,
            external_status="delivered",
            internal_status=OutboundMessageStatus.DELIVERED.value,
            now=self.now,
        )

        self.assertEqual(len(command_gateway.updates), 1)
        self.assertEqual(
            [event.event_type for event in outbox.events],
            [DELIVERY_STATUS_CHANGED_EVENT, OUTBOUND_MESSAGE_DELIVERED_EVENT],
        )

    def _outbound_row(self) -> dict:
        return {
            "id": self.outbound_id.uuid,
            "communication_request_id": self.request_id.uuid,
            "provider_connection_id": self.provider_connection_id.uuid,
            "channel_code": "sms",
            "priority": 100,
            "recipient_identifier_type": "PHONE",
            "recipient_address": "+15551234567",
            "recipient_snapshot": {"source_kind": "RAW_VALUE"},
            "rendered_payload": {},
            "provider_request_payload": {},
            "external_message_id": "external-1",
            "external_status": "accepted",
            "internal_status": OutboundMessageStatus.SENDING.value,
            "error_code": None,
            "error_message": None,
            "queued_at": self.now,
            "sent_at": None,
            "delivered_at": None,
            "failed_at": None,
            "processing_token": None,
            "processing_started_at": None,
            "processing_deadline_at": None,
            "next_attempt_at": None,
            "queue_published_at": self.now,
            "queue_publish_count": 1,
            "created_at": self.now,
            "updated_at": self.now,
        }


__all__ = ["CommunicationIntegrationEventsTests"]
