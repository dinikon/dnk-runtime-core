from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.inventory.domain.category.entity import CategoryEntity
from src.modules.inventory.domain.category.error import (
    CategoryHierarchyError,
    CategoryNotFoundError,
    InvalidCategoryNameError,
)
from src.modules.inventory.domain.category.service import CategoryService
from src.modules.inventory.domain.category.value_object import (
    CategoryIdVO,
    CategoryNameVO,
)
from src.modules.inventory.domain.product.error import (
    InvalidProductNameError,
    InvalidProductSkuError,
)
from src.modules.inventory.domain.product.service import ProductService
from src.modules.inventory.domain.product.value_object import (
    ProductIdVO,
    ProductNameVO,
    SkuVO,
)
from src.modules.shared import EntityIdVO


class ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class CategoryRepositoryStub:
    def __init__(self, categories: list[CategoryEntity] | None = None) -> None:
        self.categories = {category.id.uuid: category for category in categories or []}
        self.saved: CategoryEntity | None = None

    async def load(self, *, tenant_id, category_id):
        return self.categories.get(category_id.uuid)

    async def save(self, *, tenant_id, category):
        self.categories[category.id.uuid] = category
        self.saved = category
        return category

    async def delete(self, *, tenant_id, category_id):
        self.categories.pop(category_id.uuid, None)


class ProductRepositoryStub:
    def __init__(self) -> None:
        self.saved = None

    async def load(self, *, tenant_id, product_id):
        return (
            self.saved
            if self.saved is not None and self.saved.id == product_id
            else None
        )

    async def save(self, *, tenant_id, product):
        self.saved = product
        return product

    async def delete(self, *, tenant_id, product_id):
        self.saved = None


class InventoryDomainUseCaseTests(unittest.IsolatedAsyncioTestCase):
    def test_product_value_objects_reject_empty_values(self) -> None:
        with self.assertRaises(InvalidProductSkuError):
            SkuVO(" ")
        with self.assertRaises(InvalidProductNameError):
            ProductNameVO("")

    def test_category_name_rejects_empty_values(self) -> None:
        with self.assertRaises(InvalidCategoryNameError):
            CategoryNameVO(" ")

    async def test_product_create_preserves_optional_category(self) -> None:
        now = datetime.now(UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        category = CategoryEntity.create(
            id_=CategoryIdVO.from_value(uuid4()),
            now=now,
            name="Shoes",
        )
        product_repository = ProductRepositoryStub()
        service = ProductService(
            command_repository=product_repository,
            category_repository=CategoryRepositoryStub([category]),
            clock=ClockStub(now),
        )

        product = await service.create_product(
            tenant_id=tenant_id,
            product_id=ProductIdVO.from_value(uuid4()),
            sku=" SKU-1 ",
            product_name=" Running Shoe ",
            category_id=category.id,
        )

        self.assertEqual(product.sku.value, "SKU-1")
        self.assertEqual(product.product_name.value, "Running Shoe")
        self.assertEqual(product.category_id, category.id)
        self.assertEqual(product_repository.saved, product)

    async def test_product_create_rejects_missing_category(self) -> None:
        now = datetime.now(UTC)
        service = ProductService(
            command_repository=ProductRepositoryStub(),
            category_repository=CategoryRepositoryStub(),
            clock=ClockStub(now),
        )

        with self.assertRaises(CategoryNotFoundError):
            await service.create_product(
                tenant_id=EntityIdVO.from_value(uuid4()),
                product_id=ProductIdVO.from_value(uuid4()),
                sku="SKU-1",
                product_name="Running Shoe",
                category_id=CategoryIdVO.from_value(uuid4()),
            )

    async def test_category_reparent_rejects_self_parent(self) -> None:
        now = datetime.now(UTC)
        category_id = CategoryIdVO.from_value(uuid4())
        service = CategoryService(
            command_repository=CategoryRepositoryStub(),
            clock=ClockStub(now),
        )

        with self.assertRaises(CategoryHierarchyError):
            await service.create_category(
                tenant_id=EntityIdVO.from_value(uuid4()),
                category_id=category_id,
                name="Shoes",
                parent_category_id=category_id,
            )

    async def test_category_reparent_rejects_descendant_cycle(self) -> None:
        now = datetime.now(UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        parent = CategoryEntity.create(
            id_=CategoryIdVO.from_value(uuid4()),
            now=now,
            name="Shoes",
        )
        child = CategoryEntity.create(
            id_=CategoryIdVO.from_value(uuid4()),
            now=now,
            name="Running",
            parent_category_id=parent.id,
        )
        service = CategoryService(
            command_repository=CategoryRepositoryStub([parent, child]),
            clock=ClockStub(now),
        )

        with self.assertRaises(CategoryHierarchyError):
            await service.update_category(
                tenant_id=tenant_id,
                category_id=parent.id,
                name="Shoes",
                parent_category_id=child.id,
            )
