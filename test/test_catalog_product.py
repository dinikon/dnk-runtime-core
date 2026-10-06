"""Инварианты Product и запись контента по схеме ProductType."""

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.catalog.application.content_schema.contracts import (
    ProductTypeSchemaDTO,
    SchemaBlockDTO,
)
from src.modules.catalog.application.content_schema.normalize_content import (
    normalize_content,
)
from src.modules.catalog.application.content_schema.service import (
    SchemaConflictError,
    SchemaValidationError,
)
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
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
    ContentBlockType,
)
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.error import InvalidProductVariantError
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.domain.product_type.aggregate import (
    ContentScope,
    ProductType,
    ProductTypeContentBlock,
    InvalidProductTypeError,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.content_schema.rich_text_sanitizer import (
    Nh3RichTextSanitizer,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 10, 6, tzinfo=UTC)
        self.actor = EntityIdVO(uuid4())
        self.sku = EntityIdVO(uuid4())
        self.type_id = ProductTypeIdVO(uuid4())

    def create(self, contents=()) -> Product:
        return Product.create(
            product_id=ProductIdVO(uuid4()),
            product_type_id=self.type_id,
            variant_id=VariantIdVO(uuid4()),
            sku_id=self.sku,
            contents=contents,
            actor_id=self.actor,
            now=self.now,
        )

    def test_simple_and_audit(self) -> None:
        product = self.create()
        self.assertIs(product.kind, ProductKind.SIMPLE)
        self.assertEqual(product.product_type_id, self.type_id)
        self.assertEqual(product.variant.sku_id, self.sku)
        self.assertEqual(product.created_by, product.updated_by)
        self.assertEqual(product.created_at, product.updated_at)
        with self.assertRaises(InvalidProductVariantError):
            product.replace_variant_structure(
                kind=ProductKind.VARIABLE,
                variants=product.variants,
                actor_id=self.actor,
                now=self.now,
            )

    def test_content_values_are_immutable_and_locale_unique(self) -> None:
        block_id = uuid4()
        content = ProductContentVO(ProductLocaleVO(" uk-UA "), {block_id: "Name"})
        self.assertEqual(content.locale.value, "uk-UA")
        with self.assertRaises(TypeError):
            content.values[block_id] = "Other"
        product = self.create((content,))
        self.assertEqual(product.contents["uk-UA"].values[block_id], "Name")

    def test_same_block_allowed_in_both_scopes(self) -> None:
        block_id = ContentBlockIdVO(uuid4())
        blocks = (
            ProductTypeContentBlock(block_id, ContentScope.PRODUCT, True, 0),
            ProductTypeContentBlock(block_id, ContentScope.VARIANT, False, 0),
        )
        product_type = ProductType.create(
            id=self.type_id,
            code=" clean ",
            translations={"uk": "Чистий"},
            blocks=blocks,
        )
        self.assertEqual(len(product_type.blocks), 2)
        with self.assertRaises(InvalidProductTypeError):
            ProductType.create(
                id=self.type_id,
                code="clean",
                translations={"uk": "Чистий"},
                blocks=(blocks[0], blocks[0]),
            )


class ContentValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.block = uuid4()
        self.schema = ProductTypeSchemaDTO(
            uuid4(),
            "clean",
            True,
            1,
            {"uk": "Чистий"},
            (
                SchemaBlockDTO(
                    self.block,
                    "title",
                    ContentBlockType.TEXT,
                    ContentScope.PRODUCT,
                    True,
                    0,
                    {"uk": "Назва"},
                ),
                SchemaBlockDTO(
                    self.block,
                    "title",
                    ContentBlockType.TEXT,
                    ContentScope.VARIANT,
                    False,
                    0,
                    {"uk": "Назва"},
                ),
            ),
        )
        self.sanitizer = Nh3RichTextSanitizer()

    def test_scope_and_required_are_independent(self) -> None:
        with self.assertRaises(SchemaValidationError):
            normalize_content(
                self.schema,
                scope=ContentScope.PRODUCT,
                version=1,
                blocks={},
                sanitizer=self.sanitizer,
            )
        self.assertEqual(
            normalize_content(
                self.schema,
                scope=ContentScope.VARIANT,
                version=1,
                blocks={},
                sanitizer=self.sanitizer,
            ),
            {},
        )
        self.assertEqual(
            normalize_content(
                self.schema,
                scope=ContentScope.PRODUCT,
                version=1,
                blocks={"title": " Name "},
                sanitizer=self.sanitizer,
            ),
            {self.block: "Name"},
        )
        with self.assertRaises(SchemaConflictError):
            normalize_content(
                self.schema,
                scope=ContentScope.PRODUCT,
                version=2,
                blocks={"title": "Name"},
                sanitizer=self.sanitizer,
            )

    def test_rich_text_removes_unsafe_html(self) -> None:
        html = self.sanitizer.clean(
            '<script>alert(1)</script><p>Hello <a href="javascript:alert(2)">world</a></p>'
        )
        self.assertNotIn("script", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("Hello", html)


class ProductApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.actor = EntityIdVO(uuid4())
        self.sku = uuid4()
        self.product_id, self.variant_id = uuid4(), uuid4()
        self.title_id = uuid4()
        self.schema = ProductTypeSchemaDTO(
            uuid4(),
            "clean",
            True,
            1,
            {"uk": "Чистий"},
            (
                SchemaBlockDTO(
                    self.title_id,
                    "title",
                    ContentBlockType.TEXT,
                    ContentScope.PRODUCT,
                    True,
                    0,
                    {"uk": "Назва"},
                ),
            ),
        )
        self.repository = Mock(
            add=AsyncMock(), get_for_update=AsyncMock(), save_content=AsyncMock()
        )
        self.schemas = Mock(
            get_clean_type=AsyncMock(return_value=self.schema),
            get_type=AsyncMock(return_value=self.schema),
        )
        self.skus = Mock(get_code=AsyncMock(return_value="SKU-1"))
        self.locales = Mock(is_active=AsyncMock(return_value=True))
        self.clock = Mock(now=Mock(return_value=datetime(2026, 10, 6, tzinfo=UTC)))
        self.uuids = Mock(new=Mock(side_effect=[self.product_id, self.variant_id]))
        self.sanitizer = Nh3RichTextSanitizer()

    async def test_create_and_replace(self) -> None:
        create = CreateProductHandler(
            self.repository,
            self.skus,
            self.locales,
            self.clock,
            self.uuids,
            self.schemas,
            self.sanitizer,
        )
        result = await create.execute(
            CreateProductCommand(
                self.actor, self.sku, (CreateProductContent("uk", {"title": " Name "}),)
            )
        )
        self.assertEqual(result.product_type_id, self.schema.id)
        product = self.repository.add.await_args.args[0]
        self.assertEqual(product.contents["uk"].values[self.title_id], "Name")
        self.repository.get_for_update.return_value = product
        put = PutProductContentHandler(
            self.repository, self.locales, self.clock, self.schemas, self.sanitizer
        )
        changed = await put.execute(
            PutProductContentCommand(
                product.id, self.actor, "ru", 1, {"title": " Имя "}
            )
        )
        self.assertEqual(changed.blocks, {"title": "Имя"})
        self.assertEqual(self.repository.save_content.await_count, 1)
        self.assertEqual(product.created_at, product.updated_at)
