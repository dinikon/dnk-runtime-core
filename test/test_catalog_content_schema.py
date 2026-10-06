"""Инварианты ContentBlockDefinition и ProductType и сценарии изменения."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.catalog.application.content_block.command.put_content_block.command import (
    PutContentBlockCommand,
)
from src.modules.catalog.application.content_block.command.put_content_block.handler import (
    PutContentBlockHandler,
)
from src.modules.catalog.application.product_type.command.put_product_type.command import (
    PutProductTypeCommand,
)
from src.modules.catalog.application.product_type.command.put_product_type.handler import (
    PutProductTypeHandler,
)
from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.error import ContentBlockConflictError
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockCodeVO,
    ContentBlockIdVO,
    ContentBlockTranslationVO,
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import (
    ContentScope,
    ProductType,
    ProductTypeContentBlock,
)
from src.modules.catalog.domain.product_type.error import ProductTypeConflictError
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.product_type.persistence.schema_reader import (
    SqlAlchemyProductTypeSchemaReader,
)
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    ContentBlockDetailsDTO,
)


class ContentSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.block_id = ContentBlockIdVO(uuid4())
        self.type_id = ProductTypeIdVO(uuid4())
        self.block = ContentBlockDefinition.create(
            id=self.block_id,
            code=ContentBlockCodeVO("title"),
            type=ContentBlockType.TEXT,
            translations={"uk": ContentBlockTranslationVO("Назва")},
        )
        self.assignments = (
            ProductTypeContentBlock(self.block_id, ContentScope.PRODUCT, True, 0),
            ProductTypeContentBlock(self.block_id, ContentScope.VARIANT, False, 0),
        )
        self.product_type = ProductType.create(
            id=self.type_id,
            code="custom",
            translations={"uk": "Тип"},
            blocks=self.assignments,
        )
        self.definitions = Mock(
            get=AsyncMock(
                return_value=ContentBlockDetailsDTO(
                    self.block_id.uuid,
                    "title",
                    ContentBlockType.TEXT,
                    False,
                    {"uk": "Назва"},
                )
            )
        )
        self.locales = Mock(is_active=AsyncMock(return_value=True))

    async def test_same_block_in_both_scopes_and_schema_version(self) -> None:
        repository = Mock(
            get_for_update=AsyncMock(return_value=self.product_type), save=AsyncMock()
        )
        usage = Mock(
            content_block_in_use=AsyncMock(return_value=False),
            missing_required_value=AsyncMock(return_value=False),
        )
        handler = PutProductTypeHandler(
            repository, self.definitions, usage, self.locales
        )
        result = await handler.execute(
            PutProductTypeCommand(
                self.type_id,
                {"uk": "Новий тип"},
                self.assignments,
                1,
            )
        )
        self.assertEqual(result.schema_version, 1)
        self.assertEqual(len(result.blocks), 2)
        repository.save.assert_awaited_once()
        with self.assertRaises(ProductTypeConflictError):
            await handler.execute(
                PutProductTypeCommand(
                    self.type_id,
                    {"uk": "Тип"},
                    self.assignments,
                    2,
                )
            )

    async def test_missing_required_variant_block_rejects_change(self) -> None:
        repository = Mock(
            get_for_update=AsyncMock(return_value=self.product_type), save=AsyncMock()
        )
        usage = Mock(
            content_block_in_use=AsyncMock(return_value=False),
            missing_required_value=AsyncMock(return_value=True),
        )
        handler = PutProductTypeHandler(
            repository, self.definitions, usage, self.locales
        )
        changed = (
            self.assignments[0],
            ProductTypeContentBlock(self.block_id, ContentScope.VARIANT, True, 0),
        )
        with self.assertRaises(ProductTypeConflictError):
            await handler.execute(
                PutProductTypeCommand(self.type_id, {"uk": "Тип"}, changed, 1)
            )
        repository.save.assert_not_awaited()

    async def test_used_definition_cannot_change_type(self) -> None:
        repository = Mock(
            get_for_update=AsyncMock(return_value=self.block), save=AsyncMock()
        )
        usage = Mock(is_in_use=AsyncMock(return_value=True))
        handler = PutContentBlockHandler(repository, usage, self.locales)
        with self.assertRaises(ContentBlockConflictError):
            await handler.execute(
                PutContentBlockCommand(
                    self.block_id, ContentBlockType.RICH_TEXT, {"uk": "Назва"}
                )
            )
        repository.save.assert_not_awaited()

    async def test_system_roots_protect_structure_and_type(self) -> None:
        system_block = ContentBlockDefinition.create(
            id=self.block_id,
            code=ContentBlockCodeVO("title"),
            type=ContentBlockType.TEXT,
            translations={"uk": ContentBlockTranslationVO("Назва")},
            is_system=True,
        )
        with self.assertRaises(ContentBlockConflictError):
            system_block.change_type(ContentBlockType.RICH_TEXT)
        system_type = ProductType.create(
            id=self.type_id,
            code="clean",
            translations={"uk": "Чистий"},
            blocks=self.assignments,
            is_system=True,
        )
        with self.assertRaises(ProductTypeConflictError):
            system_type.replace_blocks((self.assignments[0],))

    async def test_schema_version_increments_only_on_structure_change(self) -> None:
        self.product_type.replace_translations({"uk": "Інша назва"})
        self.product_type.replace_blocks(self.assignments)
        self.assertEqual(self.product_type.schema_version, 1)
        self.product_type.replace_blocks((self.assignments[0],))
        self.assertEqual(self.product_type.schema_version, 2)


class ProductTypeProjectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_loads_all_types_in_batched_queries(self) -> None:
        types = [
            SimpleNamespace(
                id=uuid4(), code=f"type_{index}", is_system=False, schema_version=1
            )
            for index in range(10)
        ]
        names = [
            SimpleNamespace(product_type_id=item.id, locale_code="uk", name=item.code)
            for item in types
        ]
        block_id = uuid4()
        assignments = [
            (
                SimpleNamespace(
                    product_type_id=item.id, scope="product", required=True, position=0
                ),
                SimpleNamespace(id=block_id, code="title", type="text"),
            )
            for item in types
        ]
        block_names = [
            SimpleNamespace(block_id=block_id, locale_code="uk", name="Назва")
        ]
        session = Mock(
            execute=AsyncMock(
                side_effect=[
                    Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=types)))),
                    Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=names)))),
                    Mock(all=Mock(return_value=assignments)),
                    Mock(
                        scalars=Mock(
                            return_value=Mock(all=Mock(return_value=block_names))
                        )
                    ),
                ]
            )
        )
        result = await SqlAlchemyProductTypeSchemaReader(session).list_types()
        self.assertEqual(len(result), 10)
        self.assertEqual(len(result[0].blocks), 1)
        self.assertEqual(session.execute.await_count, 4)
