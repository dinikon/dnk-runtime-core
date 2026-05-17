from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.inventory.domain.category.entity import CategoryEntity
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.entity import ProductEntity
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.inventory.infrastructure import (
    CategoryRuntimeRepository,
    ProductRuntimeRepository,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


def _field(name: str, type_code: str, is_nullable: bool = False):
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=is_nullable,
        default_value=None,
        options={},
        settings={},
    )


def _product_descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="product",
        table_name="products",
        pk="id",
        title_field="id",
        fields=(
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("sku", "text"),
            _field("product_name", "text"),
            _field("description", "text", is_nullable=True),
            _field("category_id", "uuid", is_nullable=True),
        ),
        relations=(),
    )


def _category_descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="product_category",
        table_name="product_categories",
        pk="id",
        title_field="id",
        fields=(
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("name", "text"),
            _field("parent_category_id", "uuid", is_nullable=True),
        ),
        relations=(),
    )


class ResolverStub:
    def __init__(self, descriptor) -> None:
        self.descriptor = descriptor
        self.object_name = None

    async def resolve(self, *, tenant_id, object_name):
        self.object_name = object_name
        return self.descriptor


class InventoryRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_product_save_inserts_payload_with_optional_category(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        product_id = ProductIdVO.from_value(uuid4())
        category_id = CategoryIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        inserted_payload = None

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(self, **_kwargs):
                return []

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                nonlocal inserted_payload
                inserted_payload = payload
                return {
                    "id": product_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "sku": "SKU-1",
                    "product_name": "Running Shoe",
                    "description": "Trail shoe",
                    "category_id": category_id.uuid,
                }

            async def update(self, *, descriptor, object_id, patch):
                raise AssertionError("update should not be called")

            async def delete(self, *, descriptor, object_id):
                return True

        resolver = ResolverStub(_product_descriptor())
        repository = ProductRuntimeRepository(
            runtime_object_resolver=resolver,
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        product = await repository.save(
            tenant_id=tenant_id,
            product=ProductEntity.create(
                id_=product_id,
                now=now,
                sku="SKU-1",
                product_name="Running Shoe",
                description="Trail shoe",
                category_id=category_id,
            ),
        )

        self.assertEqual(resolver.object_name, "product")
        self.assertEqual(inserted_payload["id"], product_id.uuid)
        self.assertEqual(inserted_payload["sku"], "SKU-1")
        self.assertEqual(inserted_payload["category_id"], category_id.uuid)
        self.assertEqual(product.category_id, category_id)

    async def test_product_list_filters_by_category(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        category_id = CategoryIdVO.from_value(uuid4())
        product_id = uuid4()
        now = datetime.now(UTC)
        recorded_filters = None

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                nonlocal recorded_filters
                recorded_filters = filters
                return [
                    {
                        "id": product_id,
                        "created_at": now,
                        "updated_at": now,
                        "sku": "SKU-1",
                        "product_name": "Running Shoe",
                        "description": None,
                        "category_id": category_id.uuid,
                    }
                ]

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                return {}

            async def update(self, *, descriptor, object_id, patch):
                return None

            async def delete(self, *, descriptor, object_id):
                return True

        repository = ProductRuntimeRepository(
            runtime_object_resolver=ResolverStub(_product_descriptor()),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        result = await repository.list(
            tenant_id=tenant_id,
            limit=10,
            offset=0,
            category_id=category_id,
        )

        self.assertEqual(recorded_filters[0].field.name, "category_id")
        self.assertEqual(recorded_filters[0].value, category_id.uuid)
        self.assertEqual(result[0].category_id, category_id.uuid)

    async def test_category_save_and_list_maps_parent_category(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        category_id = CategoryIdVO.from_value(uuid4())
        parent_category_id = CategoryIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        inserted_payload = None
        recorded_filters = None

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                nonlocal recorded_filters
                recorded_filters = filters
                return [
                    {
                        "id": category_id.uuid,
                        "created_at": now,
                        "updated_at": now,
                        "name": "Running",
                        "parent_category_id": parent_category_id.uuid,
                    }
                ]

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                nonlocal inserted_payload
                inserted_payload = payload
                return {
                    "id": category_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "name": "Running",
                    "parent_category_id": parent_category_id.uuid,
                }

            async def update(self, *, descriptor, object_id, patch):
                return None

            async def delete(self, *, descriptor, object_id):
                return True

        repository = CategoryRuntimeRepository(
            runtime_object_resolver=ResolverStub(_category_descriptor()),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        category = await repository.save(
            tenant_id=tenant_id,
            category=CategoryEntity.create(
                id_=category_id,
                now=now,
                name="Running",
                parent_category_id=parent_category_id,
            ),
        )
        result = await repository.list(
            tenant_id=tenant_id,
            limit=10,
            offset=0,
            parent_category_id=parent_category_id,
        )

        self.assertEqual(
            inserted_payload["parent_category_id"], parent_category_id.uuid
        )
        self.assertEqual(category.parent_category_id, parent_category_id)
        self.assertEqual(recorded_filters[0].field.name, "parent_category_id")
        self.assertEqual(recorded_filters[0].value, parent_category_id.uuid)
        self.assertEqual(result[0].parent_category_id, parent_category_id.uuid)
