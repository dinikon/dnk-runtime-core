"""Удаление ItemPackaging через корень без обращения к типу тары или Catalog."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.inventory.application.inventory_item.command.delete_item_packaging.command import (
    DeleteItemPackagingCommand,
)
from src.modules.inventory.application.inventory_item.command.delete_item_packaging.handler import (
    DeleteItemPackagingHandler,
)
from src.modules.inventory.domain.inventory_item.entity.item_packaging import (
    ItemPackaging,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemComponentNotFoundError,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from test import test_inventory_item_packaging_mutations_application as support


class DeleteItemPackagingApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет отсутствие потерь полного агрегата и передачу отказов Domain."""

    async def asyncSetUp(self) -> None:
        """Переиспользует агрегат с двумя упаковками и независимым штрихкодом."""
        await support.ItemPackagingMutationsApplicationTests.asyncSetUp(self)
        self.handler = DeleteItemPackagingHandler(self.items)
        self.command = DeleteItemPackagingCommand(self.item.id, self.identifier)
        self.items.delete = AsyncMock()

    async def test_delete_first_middle_last_preserves_full_aggregate(self) -> None:
        """Удаляется ровно выбранная Entity, ID, порядок остальных и штрихкоды сохраняются."""
        child = self.item.packagings[0]
        third = ItemPackaging.create(
            identifier=ItemPackagingIdVO(uuid4()),
            packaging_type_id=child.packaging_type_id,
            code=PackagingCodeVO("THIRD"),
            name=child.name,
            content_quantity=child.content_quantity,
            content_uom=child.content_uom,
        )
        item = self.item.add_packaging(third, packaging_type=self.kind.snapshot())
        for index in range(3):
            with self.subTest(index=index):
                self.items.get_for_update.return_value = item
                result = await self.handler.execute(
                    DeleteItemPackagingCommand(item.id, item.packagings[index].id)
                )
                self.assertIsNone(result)
                saved = self.items.save.await_args.args[0]
                expected = tuple(p for i, p in enumerate(item.packagings) if i != index)
                self.assertEqual(saved, replace(item, packagings=expected))
                self.assertEqual(len(item.packagings), 3)
        self.types.get_for_update.assert_not_awaited()
        self.items.delete.assert_not_awaited()

    async def test_last_packaging_can_be_removed_without_deleting_item(self) -> None:
        """Пустая коллекция допустима, корень и его штрихкод остаются прежними."""
        item = self.item.remove_packaging(self.item.packagings[1].id)
        self.items.get_for_update.return_value = item
        await self.handler.execute(self.command)
        saved = self.items.save.await_args.args[0]
        self.assertEqual(saved.packagings, ())
        self.assertEqual((saved.id, saved.barcodes), (item.id, item.barcodes))
        self.items.delete.assert_not_awaited()

    async def test_missing_item_or_foreign_component_never_saves(self) -> None:
        """Отсутствие корня и упаковки остаётся предметной ошибкой, без записи."""
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.items.get_for_update.return_value = self.item
        with self.assertRaises(InventoryItemComponentNotFoundError):
            await self.handler.execute(
                replace(self.command, packaging_id=ItemPackagingIdVO(uuid4()))
            )
        self.items.save.assert_not_awaited()
        self.items.delete.assert_not_awaited()

    async def test_write_failure_is_not_swallowed(self) -> None:
        """Ошибка записи доходит до внешнего UoW, который выполнит rollback."""
        self.items.save.side_effect = RuntimeError("save unavailable")
        with self.assertRaisesRegex(RuntimeError, "save unavailable"):
            await self.handler.execute(self.command)
