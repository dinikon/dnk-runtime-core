from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequest,
    CommunicationRequestIdVO,
    IdempotencyKeyVO,
    InitiatorTypeVO,
    InvalidIdempotencyKeyError,
    InvalidInitiatorTypeError,
    InvalidOutboundPriorityError,
    InvalidRecipientAddressError,
    InvalidRecipientIdentifierTypeError,
    OutboundMessage,
    OutboundMessageIdVO,
    OutboundMessageService,
    OutboundPriorityVO,
    RecipientAddressVO,
    RecipientIdentifierTypeVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


class _ClockStub:
    def now(self):
        return datetime(2026, 5, 14, 12, 0, tzinfo=UTC)


class _OutboundRepositoryStub:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None

    async def get_existing_send_by_idempotency(self, **_kwargs):
        return None

    async def create_send_request(self, **kwargs):
        self.kwargs = kwargs
        return (
            CommunicationRequest.create(
                communication_request_id=kwargs["communication_request_id"],
                tenant_id=kwargs["tenant_id"],
                initiator_type=kwargs["initiator_type"],
                initiator_ref_id=kwargs["initiator_ref_id"],
                correlation_id=kwargs["correlation_id"],
                idempotency_key=kwargs["idempotency_key"],
                channel_code=kwargs["channel_code"],
                template_id=kwargs["template_id"],
                template_version_id=kwargs["template_version_id"],
                recipient_identifier_type=kwargs["recipient_identifier_type"],
                recipient_address=kwargs["recipient_address"],
                recipient_snapshot=kwargs["recipient_snapshot"],
                variables=kwargs["variables"],
                scheduled_at=kwargs["scheduled_at"],
                priority=kwargs["priority"],
                now=kwargs["now"],
            ),
            OutboundMessage.create_queued(
                outbound_message_id=kwargs["outbound_message_id"],
                tenant_id=kwargs["tenant_id"],
                communication_request_id=kwargs["communication_request_id"],
                provider_connection_id=kwargs["provider_connection_id"],
                channel_code=kwargs["channel_code"],
                priority=kwargs["priority"],
                recipient_identifier_type=kwargs["recipient_identifier_type"],
                recipient_address=kwargs["recipient_address"],
                recipient_snapshot=kwargs["recipient_snapshot"],
                now=kwargs["now"],
            ),
        )


class OutboundMessageDomainTests(unittest.IsolatedAsyncioTestCase):
    def test_value_objects_normalize_and_reject_invalid_values(self) -> None:
        self.assertEqual(InitiatorTypeVO(" CRM ").value, "CRM")
        for raw, expected in (
            (" api ", "API"),
            ("broadcast", "BROADCAST"),
            (" Workflow ", "WORKFLOW"),
            ("campaign", "CAMPAIGN"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(InitiatorTypeVO(raw).value, expected)
        self.assertEqual(RecipientIdentifierTypeVO(" phone ").value, "PHONE")
        self.assertEqual(RecipientAddressVO(" 380671112233 ").value, "380671112233")
        self.assertEqual(IdempotencyKeyVO(" idem-1 ").value, "idem-1")
        self.assertEqual(OutboundPriorityVO(0).value, 0)

        with self.assertRaises(InvalidInitiatorTypeError):
            InitiatorTypeVO(" ")
        with self.assertRaises(InvalidInitiatorTypeError):
            InitiatorTypeVO("manual")
        with self.assertRaises(InvalidInitiatorTypeError):
            InitiatorTypeVO(123)
        with self.assertRaises(InvalidRecipientAddressError):
            RecipientAddressVO("")
        with self.assertRaises(InvalidRecipientIdentifierTypeError):
            RecipientIdentifierTypeVO("")
        with self.assertRaises(InvalidIdempotencyKeyError):
            IdempotencyKeyVO("")
        with self.assertRaises(InvalidOutboundPriorityError):
            OutboundPriorityVO(-1)

    def test_entity_factories_normalize_values_and_set_timestamps(self) -> None:
        now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        request_id = CommunicationRequestIdVO.from_value(uuid4())
        outbound_id = OutboundMessageIdVO.from_value(uuid4())
        template_id = MessageTemplateIdVO.from_value(uuid4())
        version_id = TemplateVersionIdVO.from_value(uuid4())
        connection_id = ProviderConnectionIdVO.from_value(uuid4())
        variables = {"amount": 15000}
        correlation_id = EntityIdVO.from_value(uuid4())
        recipient_snapshot = {"source_kind": "RAW_VALUE"}

        request = CommunicationRequest.create(
            communication_request_id=request_id,
            tenant_id=tenant_id,
            initiator_type=" CRM ",
            initiator_ref_id="deal:1",
            correlation_id=correlation_id,
            idempotency_key=" idem-1 ",
            channel_code="SMS",
            template_id=template_id,
            template_version_id=version_id,
            recipient_identifier_type=" phone ",
            recipient_address=" 380671112233 ",
            recipient_snapshot=recipient_snapshot,
            variables=variables,
            scheduled_at=None,
            priority=10,
            now=now,
        )
        outbound = OutboundMessage.create_queued(
            outbound_message_id=outbound_id,
            tenant_id=tenant_id,
            communication_request_id=request_id,
            provider_connection_id=connection_id,
            channel_code="SMS",
            priority=10,
            recipient_identifier_type=" phone ",
            recipient_address=" 380671112233 ",
            recipient_snapshot=recipient_snapshot,
            now=now,
        )
        variables["amount"] = 1

        self.assertEqual(request.initiator_type, "CRM")
        self.assertEqual(request.recipient_identifier_type, "PHONE")
        self.assertEqual(request.idempotency_key, "idem-1")
        self.assertEqual(request.variables, {"amount": 15000})
        self.assertEqual(request.recipient_snapshot, {"source_kind": "RAW_VALUE"})
        self.assertEqual(request.created_at, now)
        self.assertEqual(outbound.recipient_identifier_type, "PHONE")
        self.assertEqual(outbound.recipient_snapshot, {"source_kind": "RAW_VALUE"})
        self.assertEqual(outbound.internal_status, "QUEUED")
        self.assertEqual(outbound.queued_at, now)

    async def test_service_validates_and_delegates_normalized_values(self) -> None:
        repository = _OutboundRepositoryStub()
        service = OutboundMessageService(repository=repository, clock=_ClockStub())

        request, outbound = await service.create_send_request(
            tenant_id=EntityIdVO.from_value(uuid4()),
            communication_request_id=CommunicationRequestIdVO.from_value(uuid4()),
            outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
            initiator_type=" CRM ",
            initiator_ref_id="send:1",
            correlation_id=EntityIdVO.from_value(uuid4()),
            idempotency_key=" idem-1 ",
            channel_code="SMS",
            template_id=MessageTemplateIdVO.from_value(uuid4()),
            template_version_id=TemplateVersionIdVO.from_value(uuid4()),
            recipient_identifier_type=" phone ",
            recipient_address=" 380671112233 ",
            recipient_snapshot={},
            variables={"amount": 15000},
            scheduled_at=None,
            priority=10,
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
        )

        assert repository.kwargs is not None
        self.assertEqual(repository.kwargs["initiator_type"], "CRM")
        self.assertEqual(repository.kwargs["recipient_address"], "380671112233")
        self.assertEqual(repository.kwargs["recipient_identifier_type"], "PHONE")
        self.assertEqual(request.idempotency_key, "idem-1")
        self.assertEqual(outbound.priority, 10)


__all__ = ["OutboundMessageDomainTests"]
