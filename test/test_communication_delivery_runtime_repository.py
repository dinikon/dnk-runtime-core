from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.communication.domain.delivery import (
    DeliveryAttempt,
    DeliveryAttemptIdVO,
    DeliveryEvent,
    DeliveryEventIdVO,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.domain.provider_connection import ProviderConnectionIdVO
from src.modules.communication.domain.provider_connector import ProviderConnectorCodeVO
from src.modules.communication.infrastructure.delivery import DeliveryRuntimeRepository
from src.modules.communication.infrastructure.runtime_object_names import (
    _ATTEMPT,
    _CONNECTOR,
    _EVENT,
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
            _field("outbound_message_id", "uuid"),
            _field("provider_code"),
            _field("status"),
        ),
        relations=(),
    )


class _ResolverStub:
    def __init__(self) -> None:
        self.calls = []

    async def resolve(self, *, tenant_id, object_name):
        self.calls.append((tenant_id, object_name))
        return _descriptor(object_name)


class _QueryGatewayStub:
    def __init__(self) -> None:
        self.by_id_rows = {}
        self.list_rows_by_descriptor = {}
        self.list_calls = []

    async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
        return self.by_id_rows.get((_descriptor_name(descriptor), object_id))

    async def list(
        self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
    ):
        self.list_calls.append(
            {
                "descriptor": _descriptor_name(descriptor),
                "filters": filters,
                "sorting": sorting,
                "page": page,
            }
        )
        return self.list_rows_by_descriptor.get(_descriptor_name(descriptor), [])


class _CommandGatewayStub:
    def __init__(self) -> None:
        self.inserts = []
        self.updates = []

    async def insert(self, *, descriptor, payload):
        self.inserts.append((_descriptor_name(descriptor), payload))
        return dict(payload)

    async def update(self, *, descriptor, object_id, patch):
        self.updates.append((_descriptor_name(descriptor), object_id, patch))
        return {"id": object_id, **patch}


class CommunicationDeliveryRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_delivery_attempt_inserts_explicit_id(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        attempt_id = DeliveryAttemptIdVO.from_value(uuid4())
        command = _CommandGatewayStub()
        repository = DeliveryRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=_QueryGatewayStub(),
        )
        started_at = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)

        result = await repository.save_delivery_attempt(
            tenant_id=tenant_id,
            attempt=DeliveryAttempt(
                delivery_attempt_id=attempt_id,
                outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
                attempt_no=1,
                status="STARTED",
                request_payload={"body": "hello"},
                response_payload=None,
                http_status_code=None,
                external_message_id=None,
                error_code=None,
                error_message=None,
                started_at=started_at,
                finished_at=None,
            ),
        )

        self.assertEqual(command.inserts[0][0], _ATTEMPT)
        self.assertEqual(command.inserts[0][1]["id"], attempt_id.uuid)
        self.assertEqual(result.delivery_attempt_id, attempt_id)

    async def test_add_delivery_event_inserts_explicit_id(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        event_id = DeliveryEventIdVO.from_value(uuid4())
        command = _CommandGatewayStub()
        repository = DeliveryRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=_QueryGatewayStub(),
        )
        created_at = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)

        result = await repository.add_delivery_event(
            tenant_id=tenant_id,
            event=DeliveryEvent(
                delivery_event_id=event_id,
                tenant_id=tenant_id,
                outbound_message_id=OutboundMessageIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
                external_message_id="ext-1",
                external_status="Delivered",
                internal_status="DELIVERED",
                event_type="DELIVERED",
                event_at=None,
                raw_payload={"message_id": "ext-1"},
                created_at=created_at,
            ),
        )

        self.assertEqual(command.inserts[0][0], _EVENT)
        self.assertEqual(command.inserts[0][1]["id"], event_id.uuid)
        self.assertEqual(result.delivery_event_id, event_id)
        self.assertEqual(result.created_at, created_at)

    async def test_get_active_connector_by_code_sets_runtime_filters(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        query.list_rows_by_descriptor[_CONNECTOR] = [
            {
                "id": uuid4(),
                "provider_code": "gms",
                "provider_name": "GMS",
                "version": "1.0.0",
                "connector_type": "YAML_HTTP",
                "yaml_spec": {},
                "yaml_checksum": "checksum",
                "status": "ACTIVE",
                "created_at": now,
                "updated_at": now,
            }
        ]
        repository = DeliveryRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(),
            runtime_query_gateway=query,
        )

        result = await repository.get_active_connector_by_code(
            tenant_id=tenant_id,
            provider_code=ProviderConnectorCodeVO("gms"),
        )

        self.assertEqual(result.provider_code, "gms")
        filters = query.list_calls[0]["filters"]
        self.assertEqual(filters[0].field.name, "provider_code")
        self.assertEqual(filters[1].field.name, "status")
        self.assertEqual(query.list_calls[0]["page"].limit, 1)


__all__ = ["CommunicationDeliveryRuntimeRepositoryTests"]
