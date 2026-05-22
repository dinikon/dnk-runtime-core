from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.contact_point.application import ListOwnerContactPointsQuery
from src.modules.contact_point.domain import (
    ContactPointBindingEntity,
    ContactPointBindingIdVO,
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointNotFoundError,
    ContactPointTypeVO,
    OwnerContactPointBinding,
)
from src.modules.contact_point.infrastructure import ContactPointRuntimeRepository
from src.modules.contact_point.infrastructure.runtime_object_names import (
    _CONTACT_POINT,
    _CONTACT_POINT_BINDING,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


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
    fields = (
        _field("id", "uuid"),
        _field("created_at", "datetime"),
        _field("updated_at", "datetime"),
        _field("contact_point_type"),
        _field("raw_value"),
        _field("normalized_value"),
        _field("normalized_hash"),
        _field("contact_point_id", "uuid"),
        _field("owner_object_id", "uuid"),
        _field("owner_record_id", "uuid"),
        _field("is_primary", "bool"),
        _field("is_active", "bool"),
        _field("detached_at", "datetime"),
    )
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name=object_name,
        table_name=f"{object_name}s",
        pk="id",
        title_field="id",
        fields=fields,
        relations=(),
    )


def _descriptor_name(descriptor) -> str:
    return getattr(descriptor, "object_name", descriptor)


class _ResolverStub:
    async def resolve(self, *, tenant_id, object_name):
        return _descriptor(object_name)


class _QueryGatewayStub:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}
        self.by_id: dict[tuple[str, object], dict] = {}
        self.list_calls = []
        self.get_calls = []

    async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
        self.get_calls.append((_descriptor_name(descriptor), object_id))
        return self.by_id.get((_descriptor_name(descriptor), object_id))

    async def list(
        self,
        *,
        descriptor,
        filters=(),
        sorting=(),
        page=None,
        fetch_plan=None,
    ):
        self.list_calls.append(
            {
                "descriptor": _descriptor_name(descriptor),
                "filters": filters,
                "sorting": sorting,
                "page": page,
            }
        )
        return self.rows.get(_descriptor_name(descriptor), [])


class _CommandGatewayStub:
    def __init__(self) -> None:
        self.inserts = []
        self.updates = []
        self.update_where_calls = []

    async def insert(self, *, descriptor, payload):
        self.inserts.append((_descriptor_name(descriptor), payload))
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        return {
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "detached_at": None,
            **payload,
        }

    async def update(self, *, descriptor, object_id, patch):
        self.updates.append((_descriptor_name(descriptor), object_id, patch))
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        return {
            "id": object_id,
            "created_at": now,
            "updated_at": now,
            **patch,
        }

    async def update_where(self, *, descriptor, filters, patch):
        self.update_where_calls.append((_descriptor_name(descriptor), filters, patch))
        return []


def _repository(query: _QueryGatewayStub, command: _CommandGatewayStub):
    return ContactPointRuntimeRepository(
        runtime_object_resolver=_ResolverStub(),
        runtime_command_gateway=command,
        runtime_query_gateway=query,
    )


class ContactPointRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_lookup_uses_normalized_hash_and_maps_to_hash_value(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_point_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        query = _QueryGatewayStub()
        query.rows[_CONTACT_POINT] = [
            {
                "id": contact_point_id,
                "created_at": now,
                "updated_at": now,
                "contact_point_type": "EMAIL",
                "raw_value": "User@Example.COM",
                "normalized_value": "user@example.com",
                "normalized_hash": "abc123",
            }
        ]
        repository = _repository(query, _CommandGatewayStub())

        entity = await repository.get_by_type_and_hash(
            tenant_id=tenant_id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            hash_value="abc123",
        )

        assert entity is not None
        self.assertEqual(entity.id.uuid, contact_point_id)
        self.assertEqual(entity.hash_value, "abc123")
        filters = query.list_calls[0]["filters"]
        self.assertEqual(
            [item.field.name for item in filters],
            ["contact_point_type", "normalized_hash"],
        )
        self.assertEqual([item.value for item in filters], ["EMAIL", "abc123"])

    async def test_save_contact_point_payload_writes_normalized_hash(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        contact_point_id = ContactPointIdVO.from_value(uuid4())
        query = _QueryGatewayStub()
        command = _CommandGatewayStub()
        repository = _repository(query, command)

        await repository.save_contact_point(
            tenant_id=tenant_id,
            contact_point=ContactPointEntity.create(
                id_=contact_point_id,
                now=now,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="User@Example.COM",
                normalized_value="user@example.com",
                hash_value="abc123",
            ),
        )

        payload = command.inserts[0][1]
        self.assertEqual(command.inserts[0][0], _CONTACT_POINT)
        self.assertEqual(payload["id"], contact_point_id.uuid)
        self.assertEqual(payload["normalized_hash"], "abc123")
        self.assertNotIn("display_value", payload)
        self.assertNotIn("hash_value", payload)
        self.assertNotIn("tenant_id", payload)

    async def test_binding_lookup_considers_inactive_rows(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        owner = OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(uuid4()),
            owner_record_id=EntityIdVO.from_value(uuid4()),
        )
        contact_point_id = ContactPointIdVO.from_value(uuid4())
        binding_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        query = _QueryGatewayStub()
        query.rows[_CONTACT_POINT_BINDING] = [
            {
                "id": binding_id,
                "created_at": now,
                "updated_at": now,
                "contact_point_id": contact_point_id.uuid,
                "contact_point_type": "EMAIL",
                "owner_object_id": owner.owner_object_id.uuid,
                "owner_record_id": owner.owner_record_id.uuid,
                "is_primary": False,
                "is_active": False,
                "detached_at": now,
            }
        ]
        repository = _repository(query, _CommandGatewayStub())

        binding = await repository.find_by_owner_and_contact_point(
            tenant_id=tenant_id,
            owner=owner,
            contact_point_id=contact_point_id,
        )

        assert binding is not None
        self.assertFalse(binding.is_active)
        filter_names = [item.field.name for item in query.list_calls[0]["filters"]]
        self.assertEqual(
            filter_names,
            ["owner_object_id", "owner_record_id", "contact_point_id"],
        )

    async def test_find_active_primary_filters_by_owner_type_active_and_primary(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        owner = OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(uuid4()),
            owner_record_id=EntityIdVO.from_value(uuid4()),
        )
        contact_point_id = ContactPointIdVO.from_value(uuid4())
        binding_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        query = _QueryGatewayStub()
        query.rows[_CONTACT_POINT_BINDING] = [
            {
                "id": binding_id,
                "created_at": now,
                "updated_at": now,
                "contact_point_id": contact_point_id.uuid,
                "contact_point_type": "EMAIL",
                "owner_object_id": owner.owner_object_id.uuid,
                "owner_record_id": owner.owner_record_id.uuid,
                "is_primary": True,
                "is_active": True,
                "detached_at": None,
            }
        ]
        repository = _repository(query, _CommandGatewayStub())

        binding = await repository.find_active_primary_by_owner_and_type(
            tenant_id=tenant_id,
            owner=owner,
            contact_point_type=ContactPointTypeVO.EMAIL,
        )

        assert binding is not None
        self.assertTrue(binding.is_primary)
        call = query.list_calls[0]
        self.assertEqual(
            [item.field.name for item in call["filters"]],
            [
                "owner_object_id",
                "owner_record_id",
                "contact_point_type",
                "is_active",
                "is_primary",
            ],
        )
        self.assertEqual(
            [item.value for item in call["filters"]],
            [
                owner.owner_object_id.uuid,
                owner.owner_record_id.uuid,
                "EMAIL",
                True,
                True,
            ],
        )

    async def test_find_first_active_by_owner_type_keeps_deterministic_sorting(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        owner = OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(uuid4()),
            owner_record_id=EntityIdVO.from_value(uuid4()),
        )
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        query = _QueryGatewayStub()
        query.rows[_CONTACT_POINT_BINDING] = [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "contact_point_id": uuid4(),
                "contact_point_type": "PHONE",
                "owner_object_id": owner.owner_object_id.uuid,
                "owner_record_id": owner.owner_record_id.uuid,
                "is_primary": False,
                "is_active": True,
                "detached_at": None,
            }
        ]
        repository = _repository(query, _CommandGatewayStub())

        await repository.find_first_active_by_owner_and_type(
            tenant_id=tenant_id,
            owner=owner,
            contact_point_type=ContactPointTypeVO.PHONE,
        )

        call = query.list_calls[0]
        self.assertEqual(
            [item.field.name for item in call["filters"]],
            ["owner_object_id", "owner_record_id", "contact_point_type", "is_active"],
        )
        self.assertEqual(
            [(item.field, item.direction) for item in call["sorting"]],
            [("created_at", "asc"), ("id", "asc")],
        )

    async def test_list_owner_contact_points_filters_sorts_and_maps_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        owner = OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(uuid4()),
            owner_record_id=EntityIdVO.from_value(uuid4()),
        )
        contact_point_id = uuid4()
        binding_id = uuid4()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        query = _QueryGatewayStub()
        query.rows[_CONTACT_POINT_BINDING] = [
            {
                "id": binding_id,
                "created_at": now,
                "updated_at": now,
                "contact_point_id": contact_point_id,
                "contact_point_type": "EMAIL",
                "owner_object_id": owner.owner_object_id.uuid,
                "owner_record_id": owner.owner_record_id.uuid,
                "is_primary": True,
                "is_active": True,
                "detached_at": None,
            }
        ]
        query.rows[_CONTACT_POINT] = [
            {
                "id": contact_point_id,
                "created_at": now,
                "updated_at": now,
                "contact_point_type": "EMAIL",
                "raw_value": "User@Example.COM",
                "normalized_value": "user@example.com",
                "normalized_hash": "abc123",
            }
        ]
        repository = _repository(query, _CommandGatewayStub())

        result = await repository.list_owner_contact_points(
            ListOwnerContactPointsQuery(
                tenant_id=tenant_id,
                owner_object_id=owner.owner_object_id,
                owner_record_id=owner.owner_record_id,
            )
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.items[0].binding_id, binding_id)
        self.assertEqual(result.items[0].contact_point_id, contact_point_id)
        self.assertEqual(result.items[0].contact_point_type, ContactPointTypeVO.EMAIL)
        self.assertEqual(result.items[0].raw_value, "User@Example.COM")
        self.assertEqual(result.items[0].normalized_value, "user@example.com")
        self.assertTrue(result.items[0].is_primary)
        self.assertEqual(result.items[0].created_at, now)

        binding_call = query.list_calls[0]
        self.assertEqual(binding_call["descriptor"], _CONTACT_POINT_BINDING)
        self.assertEqual(
            [item.field.name for item in binding_call["filters"]],
            ["owner_object_id", "owner_record_id", "is_active"],
        )
        self.assertEqual(
            [item.value for item in binding_call["filters"]],
            [owner.owner_object_id.uuid, owner.owner_record_id.uuid, True],
        )
        self.assertEqual(
            [(item.field, item.direction) for item in binding_call["sorting"]],
            [
                ("contact_point_type", "asc"),
                ("is_primary", "desc"),
                ("created_at", "asc"),
                ("id", "asc"),
            ],
        )

        contact_point_call = query.list_calls[1]
        self.assertEqual(contact_point_call["descriptor"], _CONTACT_POINT)
        self.assertEqual(
            [item.field.name for item in contact_point_call["filters"]],
            ["id"],
        )
        self.assertEqual(contact_point_call["filters"][0].op, "in")
        self.assertEqual(contact_point_call["filters"][0].value, [contact_point_id])

    async def test_list_owner_contact_points_raises_for_missing_contact_point(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        owner = OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(uuid4()),
            owner_record_id=EntityIdVO.from_value(uuid4()),
        )
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        query = _QueryGatewayStub()
        query.rows[_CONTACT_POINT_BINDING] = [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "contact_point_id": uuid4(),
                "contact_point_type": "EMAIL",
                "owner_object_id": owner.owner_object_id.uuid,
                "owner_record_id": owner.owner_record_id.uuid,
                "is_primary": True,
                "is_active": True,
                "detached_at": None,
            }
        ]
        query.rows[_CONTACT_POINT] = []
        repository = _repository(query, _CommandGatewayStub())

        with self.assertRaises(ContactPointNotFoundError):
            await repository.list_owner_contact_points(
                ListOwnerContactPointsQuery(
                    tenant_id=tenant_id,
                    owner_object_id=owner.owner_object_id,
                    owner_record_id=owner.owner_record_id,
                )
            )

    async def test_save_binding_payload_has_soft_detach_fields_without_removed_fields(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(uuid4()),
            owner_record_id=EntityIdVO.from_value(uuid4()),
        )
        binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            contact_point_type=ContactPointTypeVO.PHONE,
            owner=owner,
            is_primary=True,
        )
        query = _QueryGatewayStub()
        command = _CommandGatewayStub()
        repository = _repository(query, command)

        await repository.save_binding(tenant_id=tenant_id, binding=binding)

        payload = command.inserts[0][1]
        self.assertEqual(payload["contact_point_id"], binding.contact_point_id.uuid)
        self.assertEqual(payload["contact_point_type"], "PHONE")
        self.assertEqual(payload["owner_object_id"], owner.owner_object_id.uuid)
        self.assertEqual(payload["owner_record_id"], owner.owner_record_id.uuid)
        self.assertTrue(payload["is_primary"])
        self.assertTrue(payload["is_active"])
        self.assertIsNone(payload["detached_at"])
        self.assertNotIn("owner_type", payload)
        self.assertNotIn("role", payload)
        self.assertNotIn("tenant_id", payload)


__all__ = ["ContactPointRuntimeRepositoryTests"]
