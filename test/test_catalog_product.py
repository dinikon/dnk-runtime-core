"""Инварианты SIMPLE и сценарии Catalog без SQL и HTTP."""

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.catalog.application.product.command.create_product.command import (
    CreateProductCommand,
    CreateProductContent,
)
from src.modules.catalog.application.product.command.create_product.handler import (
    CreateProductHandler,
)
from src.modules.catalog.application.product.command.put_product_content.command import (
    PutProductContentCommand,
)
from src.modules.catalog.application.product.command.put_product_content.handler import (
    PutProductContentHandler,
)
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    ProductLocaleUnavailableError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
        self.actor = EntityIdVO(uuid4())
        self.sku = EntityIdVO(uuid4())

    def create(self, contents=()) -> Product:
        return Product.create(
            product_id=ProductIdVO(uuid4()),
            variant_id=VariantIdVO(uuid4()),
            sku_id=self.sku,
            contents=contents,
            actor_id=self.actor,
            now=self.now,
        )

    def test_simple_can_start_without_content_and_has_one_variant(self) -> None:
        product = self.create()
        self.assertEqual(product.type, "SIMPLE")
        self.assertEqual(product.variant.sku_id, self.sku)
        self.assertEqual(product.contents, {})
        self.assertEqual(product.created_at, product.updated_at)
        self.assertEqual(product.created_by, product.updated_by)

    def test_content_normalization_and_duplicate_locale(self) -> None:
        content = ProductContentVO(
            ProductLocaleVO(" uk-UA "), " Name ", "  Description  "
        )
        self.assertEqual(content.locale.value, "uk-UA")
        self.assertEqual(content.name, "Name")
        self.assertEqual(content.description, "Description")
        self.assertIsNone(
            ProductContentVO(ProductLocaleVO("uk"), "Name", " ").description
        )
        with self.assertRaises(InvalidProductContentError):
            self.create((content, content))
        for name in ("", " ", "x" * 256, 123):
            with self.subTest(name=name), self.assertRaises(InvalidProductContentError):
                ProductContentVO(ProductLocaleVO("uk"), name)

    def test_replace_content_preserves_original_audit(self) -> None:
        product = self.create()
        other = EntityIdVO(uuid4())
        later = datetime(2026, 10, 6, tzinfo=UTC)
        product.replace_content(
            ProductContentVO(ProductLocaleVO("sr-Latn"), "Ime"),
            actor_id=other,
            now=later,
        )
        self.assertEqual(product.contents["sr-Latn"].name, "Ime")
        self.assertEqual(product.created_by, self.actor)
        self.assertEqual(product.created_at, self.now)
        self.assertEqual(product.updated_by, other)
        self.assertEqual(product.updated_at, later)


class ProductApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.actor = EntityIdVO(uuid4())
        self.sku_id, self.product_id, self.variant_id = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
        self.repository = Mock(
            add=AsyncMock(), get_for_update=AsyncMock(), save_content=AsyncMock()
        )
        self.skus = Mock(get_code=AsyncMock(return_value="SKU-1"))
        self.locales = Mock(is_active=AsyncMock(return_value=True))
        self.clock = Mock(now=Mock(return_value=self.now))
        self.uuids = Mock(new=Mock(side_effect=(self.product_id, self.variant_id)))
        self.create_handler = CreateProductHandler(
            self.repository, self.skus, self.locales, self.clock, self.uuids
        )

    async def test_create_without_content_and_reused_sku(self) -> None:
        command = CreateProductCommand(self.actor, self.sku_id)
        result = await self.create_handler.execute(command)
        self.assertEqual(result.id, self.product_id)
        self.assertEqual(result.variant_id, self.variant_id)
        self.assertEqual(result.sku_code, "SKU-1")
        self.assertEqual(result.content_locales, ())
        self.assertEqual(result.created_at, result.updated_at)
        self.repository.add.assert_awaited_once()
        self.assertEqual(
            self.repository.add.await_args.args[0].variant.sku_id.uuid, self.sku_id
        )
        self.locales.is_active.assert_not_awaited()

    async def test_invalid_sku_and_locale_do_not_write(self) -> None:
        self.skus.get_code.return_value = None
        with self.assertRaises(ProductSkuNotFoundError):
            await self.create_handler.execute(
                CreateProductCommand(self.actor, self.sku_id)
            )
        self.repository.add.assert_not_awaited()
        self.skus.get_code.return_value = "SKU-1"
        self.locales.is_active.return_value = False
        with self.assertRaises(ProductLocaleUnavailableError):
            await self.create_handler.execute(
                CreateProductCommand(
                    self.actor,
                    self.sku_id,
                    (CreateProductContent("uk", "Name"),),
                )
            )
        self.repository.add.assert_not_awaited()

    async def test_put_replaces_content_and_preserves_aggregate(self) -> None:
        product = Product.create(
            product_id=ProductIdVO(self.product_id),
            variant_id=VariantIdVO(self.variant_id),
            sku_id=EntityIdVO(self.sku_id),
            contents=(),
            actor_id=self.actor,
            now=self.now,
        )
        self.repository.get_for_update.return_value = product
        handler = PutProductContentHandler(self.repository, self.locales, self.clock)
        result = await handler.execute(
            PutProductContentCommand(
                ProductIdVO(self.product_id), self.actor, "ru-UA", " Имя "
            )
        )
        self.assertEqual(result.name, "Имя")
        self.assertEqual(product.contents["ru-UA"].name, "Имя")
        self.repository.save_content.assert_awaited_once()
