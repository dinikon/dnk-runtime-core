"""Проверки изменения схемы контента независимо от SQL и HTTP."""

import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.catalog.application.content_schema.contracts import (
    BlockDefinitionDTO,
    ProductTypeSchemaDTO,
    SchemaBlockDTO,
)
from src.modules.catalog.application.content_schema.service import (
    ContentSchemaService,
    SchemaConflictError,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import (
    ContentScope,
    ProductTypeContentBlock,
)


class ContentSchemaServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.block_id = uuid4()
        self.type_id = uuid4()
        self.definition = BlockDefinitionDTO(
            self.block_id, "title", ContentBlockType.TEXT, False, {"uk": "Назва"}
        )
        self.product_assignment = SchemaBlockDTO(
            self.block_id,
            "title",
            ContentBlockType.TEXT,
            ContentScope.PRODUCT,
            True,
            0,
            self.definition.translations,
        )
        self.variant_assignment = SchemaBlockDTO(
            self.block_id,
            "title",
            ContentBlockType.TEXT,
            ContentScope.VARIANT,
            False,
            0,
            self.definition.translations,
        )
        self.current = ProductTypeSchemaDTO(
            self.type_id,
            "custom",
            False,
            1,
            {"uk": "Тип"},
            (self.product_assignment, self.variant_assignment),
        )
        self.repository = Mock(
            get_type=AsyncMock(return_value=self.current),
            get_block=AsyncMock(return_value=self.definition),
            update_type=AsyncMock(),
            content_block_in_use=AsyncMock(return_value=False),
            missing_required_value=AsyncMock(return_value=False),
            block_in_use=AsyncMock(return_value=False),
            delete_block=AsyncMock(),
        )
        self.service = ContentSchemaService(
            self.repository,
            Mock(is_active=AsyncMock(return_value=True)),
            Mock(new=Mock(return_value=uuid4())),
        )

    def assignments(self) -> tuple[ProductTypeContentBlock, ...]:
        return (
            ProductTypeContentBlock(
                ContentBlockIdVO(self.block_id), ContentScope.PRODUCT, True, 0
            ),
            ProductTypeContentBlock(
                ContentBlockIdVO(self.block_id), ContentScope.VARIANT, False, 0
            ),
        )

    async def test_reusing_block_in_both_scopes_and_versioning(self) -> None:
        result = await self.service.update_type(
            self.type_id, {"uk": "Новый тип"}, self.assignments(), 1
        )
        self.assertEqual(result.schema_version, 1)
        self.assertEqual(len(result.blocks), 2)
        self.repository.update_type.assert_awaited_once()

        with self.assertRaises(SchemaConflictError):
            await self.service.update_type(
                self.type_id, {"uk": "Тип"}, self.assignments(), 2
            )

    async def test_required_variant_block_rejected_if_existing_content_lacks_it(
        self,
    ) -> None:
        self.repository.missing_required_value.return_value = True
        changed = (
            self.assignments()[0],
            ProductTypeContentBlock(
                ContentBlockIdVO(self.block_id), ContentScope.VARIANT, True, 0
            ),
        )
        with self.assertRaises(SchemaConflictError):
            await self.service.update_type(self.type_id, {"uk": "Тип"}, changed, 1)
        self.repository.update_type.assert_not_awaited()

    async def test_used_definition_cannot_change_type_or_be_deleted(self) -> None:
        self.repository.block_in_use.return_value = True
        with self.assertRaises(SchemaConflictError):
            await self.service.update_block(
                self.block_id, ContentBlockType.RICH_TEXT, {"uk": "Назва"}
            )
        with self.assertRaises(SchemaConflictError):
            await self.service.delete_block(self.block_id)
        self.repository.delete_block.assert_not_awaited()
