"""Редактирование Warehouse через порты без HTTP и SQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.application.warehouse.command.update_warehouse.command import (
    UpdateWarehouseCommand,
)
from src.modules.inventory.application.warehouse.command.update_warehouse.handler import (
    UpdateWarehouseHandler,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)


class WarehouseMutationApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет семантику полей, immutable Domain и отсутствие лишней записи."""

    async def asyncSetUp(self) -> None:
        """Создаёт агрегат с основной ссылкой и write-порт."""
        self.warehouse = Warehouse.restore(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("original"),
            name=WarehouseNameVO("Name"),
            is_active=True,
            default_storage_location_id=StockLocationIdVO(uuid4()),
        )
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.warehouse), save=AsyncMock()
        )
        self.handler = UpdateWarehouseHandler(self.repository)
        self.command = UpdateWarehouseCommand(
            self.warehouse.id, frozenset({"is_active"}), is_active=False
        )

    async def test_false_deactivates_and_preserves_omitted_fields_and_reference(
        self,
    ) -> None:
        """Явный false применяет Domain-переход, не изменяя ID и пропущенные значения."""
        result = await self.handler.execute(self.command)
        self.assertFalse(result.is_active)
        self.assertEqual((result.code, result.name), ("original", "Name"))
        self.assertEqual(result.id, self.warehouse.id.uuid)
        self.assertEqual(
            result.default_storage_location_id,
            self.warehouse.default_storage_location_id.uuid,
        )
        self.assertTrue(self.warehouse.is_active)
        saved = self.repository.save.await_args.args[0]
        self.assertEqual(
            saved.default_storage_location_id,
            self.warehouse.default_storage_location_id,
        )

    async def test_full_update_and_editing_inactive_warehouse(self) -> None:
        """Разрешает смену кода и названия у неактивного склада и явную активацию."""
        self.repository.get_for_update.return_value = self.warehouse.deactivate()
        result = await self.handler.execute(
            replace(
                self.command,
                fields=frozenset({"code", "name", "is_active"}),
                code=" NEW ",
                name=" New Name ",
                is_active=True,
            )
        )
        self.assertEqual(
            (result.code, result.name, result.is_active), ("new", "New Name", True)
        )
        self.repository.save.assert_awaited_once()
        self.repository.save.reset_mock()
        result = await self.handler.execute(
            replace(self.command, fields=frozenset({"name"}), name="Blocked Name")
        )
        self.assertEqual(result.name, "Blocked Name")
        self.assertFalse(result.is_active)

    async def test_normalized_noop_and_repeated_false_do_not_save(self) -> None:
        """Сравнивает значения агрегатов, даже когда Domain возвращает новый экземпляр."""
        await self.handler.execute(
            replace(
                self.command,
                fields=frozenset({"code", "name", "is_active"}),
                code=" ORIGINAL ",
                name=" Name ",
                is_active=True,
            )
        )
        self.repository.get_for_update.return_value = self.warehouse.deactivate()
        await self.handler.execute(self.command)
        self.repository.save.assert_not_awaited()

    async def test_invalid_domain_values_and_missing_warehouse_never_save(self) -> None:
        """Ошибки VO и отсутствие записи не меняют исходное состояние."""
        for fields, values in (
            (frozenset({"code"}), {"code": " "}),
            (frozenset({"name"}), {"name": "\u200bName"}),
        ):
            with self.assertRaises(InventoryError):
                await self.handler.execute(
                    replace(self.command, fields=fields, **values)
                )
        self.repository.get_for_update.return_value = None
        with self.assertRaises(WarehouseNotFoundError):
            await self.handler.execute(self.command)
        self.repository.save.assert_not_awaited()
        self.assertTrue(self.warehouse.is_active)
