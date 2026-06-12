from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.broadcast.domain.broadcast.entity import BroadcastEntity
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.broadcast.infrastructure import BroadcastRuntimeRepository
from src.modules.runtime_data.application.models import RuntimeRowsPage
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


def _descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="broadcast",
        table_name="broadcasts",
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
                name="title",
                type_code="text",
                is_nullable=False,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="description",
                type_code="text",
                is_nullable=True,
                default_value=None,
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="status",
                type_code="text",
                is_nullable=False,
                default_value="'DRAFT'",
                options={},
                settings={},
            ),
        ),
        relations=(),
    )


class BroadcastRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_inserts_when_row_is_missing(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        broadcast_id = BroadcastIdVO.from_value(uuid4())
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
                    "id": broadcast_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "title": "June broadcast",
                    "description": "Dry run",
                    "status": "DRAFT",
                }

            async def update(self, *, descriptor, object_id, patch):
                raise AssertionError("update should not be called")

            async def delete(self, *, descriptor, object_id):
                return True

        repository = BroadcastRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )
        broadcast = BroadcastEntity.create(
            _id=broadcast_id,
            title=EntityTitleVO("June broadcast"),
            description=EntityDescriptionVO("Dry run"),
            now=now,
        )

        saved = await repository.save(
            tenant_id=tenant_id,
            broadcast=broadcast,
        )

        self.assertIsNotNone(inserted_payload)
        assert inserted_payload is not None
        self.assertEqual(inserted_payload["id"], broadcast_id.uuid)
        self.assertEqual(inserted_payload["title"], "June broadcast")
        self.assertEqual(inserted_payload["description"], "Dry run")
        self.assertEqual(inserted_payload["status"], "DRAFT")
        self.assertEqual(saved.id.uuid, broadcast_id.uuid)
        self.assertEqual(saved.title.value, "June broadcast")
        self.assertEqual(saved.description.value, "Dry run")
        self.assertEqual(saved.status.value, "DRAFT")

    async def test_load_maps_runtime_row_to_entity(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        broadcast_id = BroadcastIdVO.from_value(uuid4())
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
                    "id": broadcast_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "title": "June broadcast",
                    "description": None,
                    "status": "DRAFT",
                }

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        repository = BroadcastRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        loaded = await repository.load(
            tenant_id=tenant_id,
            broadcast_id=broadcast_id,
        )

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.id.uuid, broadcast_id.uuid)
        self.assertEqual(loaded.title.value, "June broadcast")
        self.assertIsNone(loaded.description)
        self.assertEqual(loaded.status.value, "DRAFT")

    async def test_list_searches_runtime_rows_with_default_sorting(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        broadcast_id = BroadcastIdVO.from_value(uuid4())
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
                raise AssertionError("delete should not be called")

        class QueryGatewayStub:
            query_plan = None

            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                raise AssertionError("get_by_id should not be called")

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                raise AssertionError("list should not be called")

            async def search(self, query_plan):
                self.query_plan = query_plan
                return RuntimeRowsPage(
                    rows=(
                        {
                            "id": broadcast_id.uuid,
                            "created_at": now,
                            "updated_at": now,
                            "title": "June broadcast",
                            "description": None,
                            "status": "DRAFT",
                        },
                    ),
                    total=7,
                )

        query_gateway = QueryGatewayStub()
        repository = BroadcastRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=query_gateway,
        )

        result = await repository.list(
            tenant_id=tenant_id,
            filter_dsl={"field": "status", "op": "eq", "value": "DRAFT"},
            sort_dsl=(),
            limit=25,
            offset=50,
        )

        self.assertEqual(result.total, 7)
        self.assertEqual(result.limit, 25)
        self.assertEqual(result.offset, 50)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].id, broadcast_id.uuid)
        self.assertEqual(result.items[0].title, "June broadcast")
        self.assertIsNone(result.items[0].description)
        self.assertEqual(result.items[0].status, "DRAFT")
        self.assertIsNotNone(query_gateway.query_plan)
        assert query_gateway.query_plan is not None
        self.assertEqual(query_gateway.query_plan.page.limit, 25)
        self.assertEqual(query_gateway.query_plan.page.offset, 50)
        self.assertEqual(query_gateway.query_plan.filters[0].field.name, "status")
        self.assertEqual(query_gateway.query_plan.filters[0].op, "eq")
        self.assertEqual(query_gateway.query_plan.filters[0].value, "DRAFT")
        self.assertEqual(
            [(item.field, item.direction) for item in query_gateway.query_plan.sorting],
            [("created_at", "desc"), ("id", "desc")],
        )
