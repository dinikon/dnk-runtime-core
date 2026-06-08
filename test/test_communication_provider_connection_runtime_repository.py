from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
    ProviderConnectionNotFoundError,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.communication.infrastructure.provider_connection import (
    ProviderConnectionRuntimeRepository,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _ATTEMPT,
    _CONNECTION,
    _CONNECTOR,
    _OUTBOUND,
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
            _field("provider_connector_id", "uuid"),
            _field("provider_connection_id", "uuid"),
            _field("channel_code"),
            _field("status"),
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
        self.list_rows = []
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
        descriptor_name = _descriptor_name(descriptor)
        self.list_calls.append(
            {
                "descriptor": descriptor_name,
                "filters": filters,
                "sorting": sorting,
                "page": page,
            }
        )
        return self.list_rows_by_descriptor.get(descriptor_name, self.list_rows)


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


def _connection_row(
    *,
    provider_connection_id=None,
    provider_connector_id=None,
    now: datetime | None = None,
    secrets_b64: str | None = "encoded",
) -> dict:
    now = now or datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    return {
        "id": provider_connection_id or uuid4(),
        "created_at": now,
        "updated_at": now,
        "provider_connector_id": provider_connector_id or uuid4(),
        "connection_name": "Main SMS",
        "channel_code": "SMS",
        "config": {"client_id": "abc"},
        "secret_ref": None,
        "secrets_b64": secrets_b64,
        "status": "ACTIVE",
    }


def _connector_row(provider_connector_id, *, status: str = "ACTIVE") -> dict:
    now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    return {
        "id": provider_connector_id,
        "provider_code": "gms",
        "provider_name": "GMS",
        "version": "1.0.0",
        "connector_type": "YAML_HTTP",
        "yaml_spec": {"channels": ["SMS"]},
        "yaml_checksum": "abc",
        "status": status,
        "created_at": now,
        "updated_at": now,
    }


class ProviderConnectionRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_inserts_payload_with_entity_id(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        row = _connection_row(
            provider_connection_id=provider_connection_id.uuid,
            provider_connector_id=provider_connector_id.uuid,
            now=now,
        )
        query = _QueryGatewayStub()
        command = _CommandGatewayStub(row)
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )

        entity = await repository.save(
            tenant_id=tenant_id,
            connection=ProviderConnectionEntity.create(
                provider_connection_id=provider_connection_id,
                now=now,
                tenant_id=tenant_id,
                provider_connector_id=provider_connector_id,
                connection_name="Main SMS",
                channel_code="SMS",
                config={"client_id": "abc"},
                secret_ref=None,
                secrets_b64="encoded",
            ),
        )

        payload = command.inserts[0][1]
        self.assertEqual(payload["id"], provider_connection_id.uuid)
        self.assertEqual(payload["provider_connector_id"], provider_connector_id.uuid)
        self.assertEqual(entity.provider_connection_id, provider_connection_id)

    async def test_save_updates_existing_row_and_raises_when_missing(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        row = _connection_row(
            provider_connection_id=provider_connection_id.uuid,
            provider_connector_id=provider_connector_id.uuid,
            now=now,
        )
        query = _QueryGatewayStub()
        query.by_id_rows[(_CONNECTION, provider_connection_id.uuid)] = row
        command = _CommandGatewayStub(row)
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=query,
        )
        entity = ProviderConnectionEntity.create(
            provider_connection_id=provider_connection_id,
            now=now,
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            connection_name="Main SMS",
            channel_code="SMS",
            config={"client_id": "abc"},
            secret_ref=None,
            secrets_b64="encoded",
        )

        result = await repository.save(tenant_id=tenant_id, connection=entity)

        self.assertEqual(command.updates[0][1], provider_connection_id.uuid)
        self.assertEqual(result.provider_connection_id, provider_connection_id)

        command.update_result = None
        with self.assertRaises(ProviderConnectionNotFoundError):
            await repository.save(tenant_id=tenant_id, connection=entity)

    async def test_list_connections_sorts_and_maps_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.list_rows = [_connection_row(secrets_b64="encoded")]
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connection_row()),
            runtime_query_gateway=query,
        )

        result = await repository.list_connections(tenant_id=tenant_id)

        self.assertEqual(query.list_calls[0]["descriptor"], _CONNECTION)
        self.assertEqual(query.list_calls[0]["filters"][0].field.name, "status")
        self.assertEqual(query.list_calls[0]["filters"][0].op, "neq")
        self.assertEqual(query.list_calls[0]["filters"][0].value, "ARCHIVED")
        self.assertEqual(query.list_calls[0]["sorting"][0].field, "connection_name")
        self.assertEqual(result[0].tenant_id, tenant_id.uuid)
        self.assertTrue(result[0].has_secrets)

    async def test_find_active_filters_connector_channel_status_and_limits_one(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.list_rows = [
            _connection_row(provider_connector_id=provider_connector_id.uuid)
        ]
        query.by_id_rows[(_CONNECTOR, provider_connector_id.uuid)] = _connector_row(
            provider_connector_id.uuid
        )
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connection_row()),
            runtime_query_gateway=query,
        )

        result = await repository.find_active(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            channel_code="SMS",
        )

        filters = query.list_calls[0]["filters"]
        self.assertEqual(result.provider_connector_id, provider_connector_id)
        self.assertEqual(filters[0].field.name, "provider_connector_id")
        self.assertEqual(filters[0].value, provider_connector_id.uuid)
        self.assertEqual(filters[1].field.name, "channel_code")
        self.assertEqual(filters[1].value, "SMS")
        self.assertEqual(filters[2].field.name, "status")
        self.assertEqual(filters[2].value, "ACTIVE")
        self.assertEqual(query.list_calls[0]["page"].limit, 1)

    async def test_find_active_returns_none_when_connector_is_not_active(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.list_rows = [
            _connection_row(provider_connector_id=provider_connector_id.uuid)
        ]
        query.by_id_rows[(_CONNECTOR, provider_connector_id.uuid)] = _connector_row(
            provider_connector_id.uuid,
            status="DISABLED",
        )
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connection_row()),
            runtime_query_gateway=query,
        )

        result = await repository.find_active(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            channel_code="SMS",
        )

        self.assertIsNone(result)

    async def test_load_provider_connector_maps_connector_row(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.by_id_rows[(_CONNECTOR, provider_connector_id.uuid)] = _connector_row(
            provider_connector_id.uuid
        )
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connection_row()),
            runtime_query_gateway=query,
        )

        result = await repository.load_provider_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )

        self.assertEqual(result.provider_connector_id, provider_connector_id)
        self.assertEqual(result.yaml_spec, {"channels": ["SMS"]})

    async def test_has_usage_checks_outbound_attempt_and_event_rows(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        query.list_rows_by_descriptor[_ATTEMPT] = [
            {"provider_connection_id": provider_connection_id.uuid}
        ]
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(_connection_row()),
            runtime_query_gateway=query,
        )

        result = await repository.has_usage(
            tenant_id=tenant_id,
            provider_connection_id=provider_connection_id,
        )

        self.assertTrue(result)
        self.assertEqual(
            [call["descriptor"] for call in query.list_calls],
            [_OUTBOUND, _ATTEMPT],
        )
        self.assertEqual(
            query.list_calls[1]["filters"][0].field.name,
            "provider_connection_id",
        )

    async def test_delete_calls_runtime_gateway(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        command = _CommandGatewayStub(_connection_row())
        repository = ProviderConnectionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command,
            runtime_query_gateway=_QueryGatewayStub(),
        )

        await repository.delete(
            tenant_id=tenant_id,
            provider_connection_id=provider_connection_id,
        )

        self.assertEqual(_descriptor_name(command.deletes[0][0]), _CONNECTION)
        self.assertEqual(command.deletes[0][1], provider_connection_id.uuid)


__all__ = ["ProviderConnectionRuntimeRepositoryTests"]
