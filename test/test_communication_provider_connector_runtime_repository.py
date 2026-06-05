from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.communication.domain.provider_connector import (
    ProviderChannelCodeVO,
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
    ProviderConnectorNameVO,
    ProviderConnectorVersionVO,
    ProviderMessageTypeCodeVO,
    ProviderMessageTypeNameVO,
)
from src.modules.communication.infrastructure.provider_connector import (
    ProviderConnectorRuntimeRepository,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _CONNECTION,
    _CONNECTOR,
    _MESSAGE_TYPE,
    _TEMPLATE,
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
            _field("provider_code"),
            _field("version"),
            _field("status"),
            _field("provider_connector_id", "uuid"),
            _field("message_type_code"),
        ),
        relations=(),
    )


class _ResolverStub:
    def __init__(self) -> None:
        self.calls: list[tuple[EntityIdVO, str]] = []

    async def resolve(self, *, tenant_id, object_name):
        self.calls.append((tenant_id, object_name))
        return _descriptor(object_name)


class _QueryGatewayStub:
    def __init__(self) -> None:
        self.by_id_rows = {}
        self.list_rows_by_descriptor = {}
        self.get_calls = []
        self.list_calls = []

    async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
        descriptor_name = _descriptor_name(descriptor)
        self.get_calls.append((descriptor_name, object_id))
        return self.by_id_rows.get((descriptor_name, object_id))

    async def list(
        self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
    ):
        self.list_calls.append(
            {
                "descriptor": descriptor,
                "filters": filters,
                "sorting": sorting,
                "page": page,
            }
        )
        return self.list_rows_by_descriptor.get(_descriptor_name(descriptor), [])


class _CommandGatewayStub:
    def __init__(self, row) -> None:
        self.row = row
        self.inserts = []
        self.updates = []
        self.deletes = []
        self.update_result = row

    async def insert(self, *, descriptor, payload):
        self.inserts.append((descriptor, payload))
        return self.row | payload

    async def update(self, *, descriptor, object_id, patch):
        self.updates.append((descriptor, object_id, patch))
        return self.update_result

    async def delete(self, *, descriptor, object_id):
        self.deletes.append((descriptor, object_id))
        return True


def _connector_row(provider_connector_id=None) -> dict:
    now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    return {
        "id": provider_connector_id or uuid4(),
        "provider_code": "gms",
        "provider_name": "GMS",
        "version": "1.0.0",
        "connector_type": "YAML_HTTP",
        "yaml_spec": {
            "channels": ["SMS"],
            "config_schema": {"type": "object"},
            "secrets_schema": {"type": "object"},
        },
        "yaml_checksum": "abc",
        "status": "ACTIVE",
        "created_at": now,
        "updated_at": now,
    }


def _message_type_row(provider_connector_id=None) -> dict:
    return {
        "id": uuid4(),
        "provider_connector_id": provider_connector_id or uuid4(),
        "message_type_code": "sms_text",
        "channel_code": "SMS",
        "name": "SMS text",
        "field_schema": {"type": "object"},
        "ui_schema": {},
        "is_active": True,
    }


class ProviderConnectorRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_upsert_connector_inserts_payload_with_entity_id(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        row = _connector_row(provider_connector_id.uuid)
        query = _QueryGatewayStub()
        command = _CommandGatewayStub(row)
        repository = ProviderConnectorRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )

        result = await repository.upsert_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            provider_code=ProviderConnectorCodeVO("gms"),
            provider_name=ProviderConnectorNameVO("GMS"),
            version=ProviderConnectorVersionVO("1.0.0"),
            connector_type="YAML_HTTP",
            yaml_spec=row["yaml_spec"],
            yaml_checksum="abc",
            status="ACTIVE",
        )

        payload = command.inserts[0][1]
        filters = query.list_calls[0]["filters"]
        self.assertEqual(payload["id"], provider_connector_id.uuid)
        self.assertEqual(filters[0].field.name, "provider_code")
        self.assertEqual(filters[0].value, "gms")
        self.assertEqual(filters[1].field.name, "version")
        self.assertEqual(filters[1].value, "1.0.0")
        self.assertEqual(result.provider_connector_id, provider_connector_id)

    async def test_upsert_connector_updates_existing_row(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        row = _connector_row(provider_connector_id.uuid)
        query = _QueryGatewayStub()
        query.list_rows_by_descriptor[_CONNECTOR] = [row]
        command = _CommandGatewayStub(row)
        repository = ProviderConnectorRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )

        result = await repository.upsert_connector(
            tenant_id=tenant_id,
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            provider_code=ProviderConnectorCodeVO("gms"),
            provider_name=ProviderConnectorNameVO("GMS"),
            version=ProviderConnectorVersionVO("1.0.0"),
            connector_type="YAML_HTTP",
            yaml_spec=row["yaml_spec"],
            yaml_checksum="abc",
            status="ACTIVE",
        )

        self.assertEqual(command.updates[0][1], provider_connector_id.uuid)
        self.assertEqual(result.provider_connector_id, provider_connector_id)
        self.assertEqual(command.inserts, [])

    async def test_upsert_message_type_filters_by_connector_and_code(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        row = _message_type_row(provider_connector_id.uuid)
        query = _QueryGatewayStub()
        command = _CommandGatewayStub(row)
        repository = ProviderConnectorRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )

        result = await repository.upsert_message_type(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            message_type_code=ProviderMessageTypeCodeVO("sms_text"),
            channel_code=ProviderChannelCodeVO("SMS"),
            name=ProviderMessageTypeNameVO("SMS text"),
            field_schema={"type": "object"},
            ui_schema={},
            is_active=True,
        )

        filters = query.list_calls[0]["filters"]
        self.assertEqual(
            _descriptor_name(query.list_calls[0]["descriptor"]), _MESSAGE_TYPE
        )
        self.assertEqual(filters[0].field.name, "provider_connector_id")
        self.assertEqual(filters[0].value, provider_connector_id.uuid)
        self.assertEqual(filters[1].field.name, "message_type_code")
        self.assertEqual(filters[1].value, "sms_text")
        self.assertEqual(result.provider_connector_id, provider_connector_id)

    async def test_list_connectors_and_message_types_map_dtos(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = uuid4()
        query = _QueryGatewayStub()
        query.list_rows_by_descriptor[_CONNECTOR] = [
            _connector_row(provider_connector_id)
        ]
        query.list_rows_by_descriptor[_MESSAGE_TYPE] = [
            _message_type_row(provider_connector_id)
        ]
        repository = ProviderConnectorRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connector_row()),
            runtime_query_gateway=query,
        )

        connectors = await repository.list_connectors(tenant_id=tenant_id)
        message_types = await repository.list_message_types(tenant_id=tenant_id)

        self.assertEqual(connectors[0].provider_connector_id, provider_connector_id)
        self.assertEqual(connectors[0].channels, ["SMS"])
        self.assertEqual(message_types[0].provider_connector_id, provider_connector_id)
        self.assertEqual(message_types[0].message_type_code, "sms_text")
        connector_filters = query.list_calls[0]["filters"]
        message_type_filters = query.list_calls[-1]["filters"]
        self.assertEqual(connector_filters[0].field.name, "status")
        self.assertEqual(connector_filters[0].op, "neq")
        self.assertEqual(connector_filters[0].value, "ARCHIVED")
        self.assertEqual(message_type_filters[0].field.name, "provider_connector_id")
        self.assertEqual(message_type_filters[0].op, "in")
        self.assertEqual(message_type_filters[0].value, [provider_connector_id])

    async def test_load_connector_and_usage_checks(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.by_id_rows[(_CONNECTOR, provider_connector_id.uuid)] = _connector_row(
            provider_connector_id.uuid
        )
        query.list_rows_by_descriptor[_TEMPLATE] = [
            {"provider_connector_id": provider_connector_id.uuid}
        ]
        repository = ProviderConnectorRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connector_row()),
            runtime_query_gateway=query,
        )

        connector = await repository.load_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        has_usage = await repository.has_usage(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )

        self.assertEqual(connector.provider_connector_id, provider_connector_id)
        self.assertTrue(has_usage)
        self.assertEqual(
            [_descriptor_name(call["descriptor"]) for call in query.list_calls],
            [_CONNECTION, _TEMPLATE],
        )

    async def test_delete_connector_calls_runtime_gateway(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        command = _CommandGatewayStub(_connector_row())
        repository = ProviderConnectorRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=_QueryGatewayStub(),
        )

        await repository.delete_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )

        self.assertEqual(_descriptor_name(command.deletes[0][0]), _CONNECTOR)
        self.assertEqual(command.deletes[0][1], provider_connector_id.uuid)


__all__ = ["ProviderConnectorRuntimeRepositoryTests"]
