from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.infrastructure.outbound_message import (
    OutboundMessageRuntimeRepository,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _OUTBOUND,
    _REQUEST,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


def _descriptor_name(descriptor) -> str:
    return getattr(descriptor, "object_name", descriptor)


def _field(name: str, type_code: str = "text") -> RuntimeFieldDescriptor:
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=True,
        default_value=None,
        options={},
        settings={},
    )


def _descriptor(object_name: str) -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name=object_name,
        table_name=object_name,
        pk="id",
        title_field="id",
        fields=(
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("communication_request_id", "uuid"),
            _field("idempotency_key"),
            _field("internal_status"),
            _field("next_attempt_at", "datetime"),
            _field("queue_published_at", "datetime"),
            _field("processing_deadline_at", "datetime"),
            _field("processing_started_at", "datetime"),
            _field("processing_token", "uuid"),
            _field("template_code"),
            _field("template_id", "uuid"),
            _field("status"),
            _field("provider_connector_id", "uuid"),
            _field("channel_code"),
            _field("recipient_identifier_type"),
            _field("recipient_snapshot", "json"),
        ),
        relations=(),
    )


class _ResolverStub:

    def __init__(self, events: list[tuple[str, str]] | None = None) -> None:
        self.calls: list[tuple[EntityIdVO, str]] = []
        self.events = events

    async def resolve(self, *, tenant_id, object_name):
        self.calls.append((tenant_id, object_name))
        if self.events is not None:
            self.events.append(("resolve", object_name))
        return _descriptor(object_name)


class _QueryGatewayStub:

    def __init__(self, events: list[tuple[str, str]] | None = None) -> None:
        self.by_id_rows = {}
        self.list_rows_by_descriptor = {}
        self.get_calls = []
        self.list_calls = []
        self.events = events

    async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
        descriptor_name = _descriptor_name(descriptor)
        self.get_calls.append((descriptor_name, object_id))
        if self.events is not None:
            self.events.append(("get", descriptor_name))
        return self.by_id_rows.get((descriptor_name, object_id))

    async def list(
        self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
    ):
        descriptor_name = _descriptor_name(descriptor)
        self.list_calls.append(
            {
                "descriptor": descriptor_name,
                "filters": filters,
                "sorting": sorting,
                "page": page,
            }
        )
        if self.events is not None:
            self.events.append(("list", descriptor_name))
        return self.list_rows_by_descriptor.get(descriptor_name, [])


class _CommandGatewayStub:

    def __init__(self, events: list[tuple[str, str]] | None = None) -> None:
        self.inserts = []
        self.updates = []
        self.claims = []
        self.update_where_calls = []
        self.locks = []
        self.events = events

    async def acquire_advisory_xact_lock(self, key: str) -> None:
        self.locks.append(key)
        if self.events is not None:
            self.events.append(("lock", key))

    async def insert(self, *, descriptor, payload):
        descriptor_name = _descriptor_name(descriptor)
        self.inserts.append((descriptor_name, payload))
        now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        defaults = {"created_at": now, "updated_at": now}
        if descriptor_name == _OUTBOUND:
            defaults |= {
                "external_message_id": None,
                "external_status": None,
                "error_code": None,
                "error_message": None,
                "sent_at": None,
                "delivered_at": None,
                "failed_at": None,
                "processing_token": None,
                "processing_started_at": None,
                "processing_deadline_at": None,
                "next_attempt_at": None,
                "queue_published_at": None,
                "queue_publish_count": 0,
            }
        return defaults | dict(payload)

    async def update(self, *, descriptor, object_id, patch):
        self.updates.append((_descriptor_name(descriptor), object_id, patch))
        return {"id": object_id, **patch}

    async def update_where(self, *, descriptor, filters, patch):
        self.update_where_calls.append((_descriptor_name(descriptor), filters, patch))
        return []

    async def claim(self, *, descriptor, filters, patch, sorting=(), limit=1):
        self.claims.append(
            {
                "descriptor": _descriptor_name(descriptor),
                "filters": filters,
                "patch": patch,
                "sorting": sorting,
                "limit": limit,
            }
        )
        return []


def _outbound_row(
    *,
    outbound_message_id=None,
    communication_request_id=None,
    provider_connection_id=None,
    queue_publish_count: int = 0,
) -> dict:
    now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    return {
        "id": outbound_message_id or uuid4(),
        "communication_request_id": communication_request_id or uuid4(),
        "provider_connection_id": provider_connection_id or uuid4(),
        "channel_code": "SMS",
        "message_class": "TRANSACTIONAL",
        "priority": 10,
        "recipient_identifier_type": "PHONE",
        "recipient_address": "380671112233",
        "recipient_snapshot": {"source_kind": "RAW_VALUE"},
        "rendered_payload": {},
        "provider_request_payload": {},
        "external_message_id": None,
        "external_status": None,
        "internal_status": "QUEUED",
        "error_code": None,
        "error_message": None,
        "queued_at": now,
        "sent_at": None,
        "delivered_at": None,
        "failed_at": None,
        "processing_token": None,
        "processing_started_at": None,
        "processing_deadline_at": None,
        "next_attempt_at": None,
        "queue_published_at": None,
        "queue_publish_count": queue_publish_count,
        "created_at": now,
        "updated_at": now,
    }


def _request_row(
    *,
    communication_request_id=None,
    idempotency_key: str = "idem-1",
) -> dict:
    now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    return {
        "id": communication_request_id or uuid4(),
        "initiator_type": "API",
        "initiator_ref_id": "manual:1",
        "correlation_id": uuid4(),
        "idempotency_key": idempotency_key,
        "message_class": "TRANSACTIONAL",
        "channel_code": "SMS",
        "template_id": uuid4(),
        "template_version_id": uuid4(),
        "recipient_identifier_type": "PHONE",
        "recipient_address": "380671112233",
        "recipient_snapshot": {"source_kind": "RAW_VALUE"},
        "variables": {"amount": 15000},
        "scheduled_at": None,
        "priority": 10,
        "status": "QUEUED",
        "created_at": now,
        "updated_at": now,
    }


class OutboundMessageRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_send_request_inserts_request_and_outbound_rows(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        request_id = CommunicationRequestIdVO.from_value(uuid4())
        outbound_id = OutboundMessageIdVO.from_value(uuid4())
        template_id = MessageTemplateIdVO.from_value(uuid4())
        version_id = TemplateVersionIdVO.from_value(uuid4())
        connection_id = ProviderConnectionIdVO.from_value(uuid4())
        command = _CommandGatewayStub()
        repository = OutboundMessageRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=_QueryGatewayStub(),
        )

        request, outbound = await repository.create_send_request(
            tenant_id=tenant_id,
            communication_request_id=request_id,
            outbound_message_id=outbound_id,
            initiator_type="CRM",
            initiator_ref_id="send:1",
            correlation_id=EntityIdVO.from_value(uuid4()),
            idempotency_key="idem-1",
            message_class="TRANSACTIONAL",
            channel_code="SMS",
            template_id=template_id,
            template_version_id=version_id,
            recipient_identifier_type="PHONE",
            recipient_address="380671112233",
            recipient_snapshot={"source_kind": "RAW_VALUE"},
            variables={"amount": 15000},
            scheduled_at=None,
            priority=10,
            provider_connection_id=connection_id,
            now=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
        )

        request_payload = command.inserts[0][1]
        outbound_payload = command.inserts[1][1]
        self.assertEqual(command.inserts[0][0], _REQUEST)
        self.assertEqual(command.inserts[1][0], _OUTBOUND)
        self.assertEqual(request_payload["id"], request_id.uuid)
        self.assertNotIn("contact_id", request_payload)
        self.assertEqual(request_payload["recipient_identifier_type"], "PHONE")
        self.assertEqual(
            request_payload["recipient_snapshot"], {"source_kind": "RAW_VALUE"}
        )
        self.assertEqual(outbound_payload["id"], outbound_id.uuid)
        self.assertEqual(outbound_payload["communication_request_id"], request_id.uuid)
        self.assertNotIn("contact_id", outbound_payload)
        self.assertEqual(outbound_payload["recipient_identifier_type"], "PHONE")
        self.assertEqual(
            outbound_payload["recipient_snapshot"], {"source_kind": "RAW_VALUE"}
        )
        self.assertEqual(request.communication_request_id, request_id)
        self.assertEqual(outbound.outbound_message_id, outbound_id)

    async def test_idempotency_lookup_takes_advisory_lock_before_query(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        request_id = uuid4()
        outbound_id = uuid4()
        events: list[tuple[str, str]] = []
        command = _CommandGatewayStub(events)
        query = _QueryGatewayStub(events)
        query.list_rows_by_descriptor[_REQUEST] = [
            _request_row(
                communication_request_id=request_id,
                idempotency_key="idem-1",
            )
        ]
        query.list_rows_by_descriptor[_OUTBOUND] = [
            _outbound_row(
                outbound_message_id=outbound_id,
                communication_request_id=request_id,
            )
        ]
        repository = OutboundMessageRuntimeRepository(
            runtime_object_resolver=_ResolverStub(events),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )

        existing = await repository.get_existing_send_by_idempotency(
            tenant_id=tenant_id,
            idempotency_key=" idem-1 ",
        )

        expected_lock = f"communication_send_idempotency:{tenant_id.uuid}:idem-1"
        self.assertIsNotNone(existing)
        self.assertEqual(command.locks, [expected_lock])
        self.assertEqual(events[0], ("lock", expected_lock))
        self.assertEqual(events[1], ("resolve", _REQUEST))
        self.assertEqual(query.list_calls[0]["descriptor"], _REQUEST)
        self.assertEqual(
            query.list_calls[0]["filters"][0].value,
            "idem-1",
        )

    async def test_list_outbound_maps_dto_and_sets_page_spec(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        outbound_id = uuid4()
        query = _QueryGatewayStub()
        query.list_rows_by_descriptor[_OUTBOUND] = [
            _outbound_row(outbound_message_id=outbound_id)
        ]
        repository = OutboundMessageRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(),
            runtime_query_gateway=query,
        )

        result = await repository.list_outbound(
            tenant_id=tenant_id,
            limit=25,
            offset=50,
        )

        self.assertEqual(result[0].outbound_message_id, outbound_id)
        self.assertEqual(result[0].tenant_id, tenant_id.uuid)
        self.assertEqual(result[0].recipient_identifier_type, "PHONE")
        self.assertEqual(result[0].recipient_snapshot, {"source_kind": "RAW_VALUE"})
        self.assertEqual(query.list_calls[0]["descriptor"], _OUTBOUND)
        self.assertEqual(query.list_calls[0]["sorting"][0].field, "created_at")
        self.assertEqual(query.list_calls[0]["page"].limit, 25)
        self.assertEqual(query.list_calls[0]["page"].offset, 50)

    async def test_mark_outbound_published_updates_publish_snapshot(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        outbound_id = OutboundMessageIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.by_id_rows[(_OUTBOUND, outbound_id.uuid)] = _outbound_row(
            outbound_message_id=outbound_id.uuid,
            queue_publish_count=2,
        )
        command = _CommandGatewayStub()
        repository = OutboundMessageRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )
        published_at = datetime(2026, 5, 14, 13, 0, tzinfo=UTC)

        await repository.mark_outbound_published(
            tenant_id=tenant_id,
            outbound_message_id=outbound_id,
            published_at=published_at,
        )

        self.assertEqual(command.updates[0][0], _OUTBOUND)
        self.assertEqual(command.updates[0][1], outbound_id.uuid)
        self.assertEqual(command.updates[0][2]["queue_published_at"], published_at)
        self.assertEqual(command.updates[0][2]["queue_publish_count"], 3)


__all__ = ["OutboundMessageRuntimeRepositoryTests"]
