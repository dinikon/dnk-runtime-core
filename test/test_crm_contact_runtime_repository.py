from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.infrastructure import ContactRuntimeRepository
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


def _descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="contact",
        table_name="contacts",
        pk="id",
        title_field="id",
        fields=(
            RuntimeFieldDescriptor(
                name="id",
                type_code="uuid",
                is_nullable=False,
                default_value="gen_random_uuid()",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="created_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="updated_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="last_name",
                type_code="text",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="first_name",
                type_code="text",
                is_nullable=False,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="middle_name",
                type_code="text",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
            ),
        ),
        relations=(),
    )


class ContactRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_inserts_when_row_is_missing(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        inserted_payload = None

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                nonlocal inserted_payload
                inserted_payload = payload
                return {
                    "id": contact_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "last_name": "Doe",
                    "first_name": "Jane",
                    "middle_name": None,
                }

            async def update(self, *, descriptor, object_id, patch):
                return None

            async def delete(self, *, descriptor, object_id):
                return True

        repository = ContactRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        contact = await repository.save(
            tenant_id=tenant_id,
            contact=type(
                "ContactStub",
                (),
                {
                    "id": contact_id,
                    "contact_name": type(
                        "Name",
                        (),
                        {
                            "last_name": "Doe",
                            "first_name": "Jane",
                            "middle_name": None,
                        },
                    )(),
                },
            )(),
        )

        self.assertEqual(inserted_payload["id"], contact_id.uuid)
        self.assertEqual(contact.id.uuid, contact_id.uuid)
        self.assertEqual(contact.contact_name.last_name, "Doe")

    async def test_get_by_id_maps_runtime_row_to_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                raise AssertionError("insert should not be called")

            async def update(self, *, descriptor, object_id, patch):
                raise AssertionError("update should not be called")

            async def delete(self, *, descriptor, object_id):
                return True

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return {
                    "id": contact_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "last_name": "Doe",
                    "first_name": "Jane",
                    "middle_name": None,
                }

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        repository = ContactRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        dto = await repository.get_by_id(
            tenant_id=tenant_id,
            contact_id=contact_id,
        )

        self.assertIsNotNone(dto)
        assert dto is not None
        self.assertEqual(dto.id, contact_id.uuid)
        self.assertEqual(dto.last_name, "Doe")

    async def test_delete_raises_when_nothing_removed(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                return {}

            async def update(self, *, descriptor, object_id, patch):
                return None

            async def delete(self, *, descriptor, object_id):
                return False

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        repository = ContactRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        with self.assertRaises(ContactNotFoundError):
            await repository.delete(
                tenant_id=tenant_id,
                contact_id=contact_id,
            )

    async def test_get_by_id_allows_nullable_last_name(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                raise AssertionError("insert should not be called")

            async def update(self, *, descriptor, object_id, patch):
                raise AssertionError("update should not be called")

            async def delete(self, *, descriptor, object_id):
                return True

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return {
                    "id": contact_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "last_name": None,
                    "first_name": "",
                    "middle_name": None,
                }

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        repository = ContactRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        dto = await repository.get_by_id(
            tenant_id=tenant_id,
            contact_id=contact_id,
        )

        self.assertIsNotNone(dto)
        assert dto is not None
        self.assertIsNone(dto.last_name)
        self.assertEqual(dto.first_name, "")
