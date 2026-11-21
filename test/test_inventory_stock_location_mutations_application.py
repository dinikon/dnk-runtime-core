"""Редактирование локаций через порты и Domain без HTTP и PostgreSQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.application.stock_location.command.update_stock_location.command import (
    UpdateStockLocationCommand,
)
from src.modules.inventory.application.stock_location.command.update_stock_location.handler import (
    UpdateStockLocationHandler,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import (
    WarehouseNotFoundError,
    DefaultStorageLocationInUseError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)


class StockLocationMutationsApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет порядок блокировок, immutable Domain и отсутствие лишней записи."""

    async def asyncSetUp(self) -> None:
        """Готовит склад с основной STORAGE и отдельную дочернюю локацию."""
        warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("main"),
            name=WarehouseNameVO("Main"),
        )
        self.default = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=warehouse.snapshot(),
            code=LocationCodeVO("storage"),
            name=LocationNameVO("Storage"),
            location_type=LocationType.STORAGE,
        )
        self.warehouse = warehouse.set_default_storage_location(self.default.snapshot())
        self.location = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            parent=self.default.snapshot(),
            code=LocationCodeVO("original"),
            name=LocationNameVO("Original"),
            location_type=LocationType.RECEIVING,
        )
        self.warehouses = Mock(
            get_for_share=AsyncMock(return_value=self.warehouse), save=AsyncMock()
        )
        self.locations = Mock(
            get_for_update=AsyncMock(return_value=self.location), save=AsyncMock()
        )
        self.handler = UpdateStockLocationHandler(self.warehouses, self.locations)
        self.command = UpdateStockLocationCommand(
            self.warehouse.id,
            self.location.id,
            frozenset({"is_active"}),
            is_active=False,
        )

    async def test_false_preserves_omitted_fields_and_all_fixed_identity(self) -> None:
        """Изменяет только локальную активность, сначала блокируя склад, затем адрес."""
        order = Mock()
        order.attach_mock(self.warehouses.get_for_share, "warehouse")
        order.attach_mock(self.locations.get_for_update, "location")
        result = await self.handler.execute(self.command)
        self.assertEqual(
            [call[0] for call in order.mock_calls], ["warehouse", "location"]
        )
        self.locations.get_for_update.assert_awaited_once_with(
            self.location.id, warehouse_id=self.warehouse.id
        )
        self.assertEqual(
            (
                result.id,
                result.warehouse_id,
                result.parent_location_id,
                result.location_type,
            ),
            (
                self.location.id.uuid,
                self.warehouse.id.uuid,
                self.default.id.uuid,
                LocationType.RECEIVING,
            ),
        )
        self.assertEqual(
            (result.code, result.name, result.is_active),
            ("original", "Original", False),
        )
        self.assertTrue(self.location.is_active)
        self.warehouses.save.assert_not_awaited()
        self.locations.save.assert_awaited_once()

    async def test_edit_and_activation_are_allowed_with_inactive_warehouse(
        self,
    ) -> None:
        """Настройка локальной карточки не активирует склад и не проверяет доступность операций."""
        self.warehouses.get_for_share.return_value = self.warehouse.deactivate()
        self.locations.get_for_update.return_value = self.location.deactivate(
            warehouse=self.warehouse.snapshot()
        )
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
        self.warehouses.save.assert_not_awaited()
        self.assertFalse(self.warehouses.get_for_share.return_value.is_active)

    async def test_main_storage_rename_allowed_but_deactivation_always_rejected(
        self,
    ) -> None:
        """Проверяет основную ссылку и при неактивном складе, и перед пропуском no-op."""
        self.locations.get_for_update.return_value = self.default
        command = replace(
            self.command,
            location_id=self.default.id,
            fields=frozenset({"name"}),
            name="Renamed",
        )
        result = await self.handler.execute(command)
        self.assertEqual(result.name, "Renamed")
        self.locations.save.reset_mock()
        for active_warehouse in (True, False):
            self.warehouses.get_for_share.return_value = (
                self.warehouse if active_warehouse else self.warehouse.deactivate()
            )
            for active_location in (True, False):
                self.locations.get_for_update.return_value = replace(
                    self.default, is_active=active_location
                )
                with (
                    self.subTest(
                        active_warehouse=active_warehouse,
                        active_location=active_location,
                    ),
                    self.assertRaises(DefaultStorageLocationInUseError),
                ):
                    await self.handler.execute(
                        replace(
                            command,
                            fields=frozenset({"name", "is_active"}),
                            name="Must roll back",
                            is_active=False,
                        )
                    )
        self.locations.save.assert_not_awaited()
        self.assertEqual(self.default.name.value, "Storage")

    async def test_normalized_noop_and_repeated_false_do_not_save(self) -> None:
        """Сравнивает итоговые значения даже при новых экземплярах из Domain-методов."""
        await self.handler.execute(
            replace(
                self.command,
                fields=frozenset({"code", "name", "is_active"}),
                code=" ORIGINAL ",
                name=" Original ",
                is_active=True,
            )
        )
        self.locations.get_for_update.return_value = self.location.deactivate(
            warehouse=self.warehouse.snapshot()
        )
        await self.handler.execute(self.command)
        self.locations.save.assert_not_awaited()

    async def test_missing_warehouse_or_location_never_saves(self) -> None:
        """Отсутствующие корни не превращаются в создание и не меняют другой адрес."""
        self.warehouses.get_for_share.return_value = None
        with self.assertRaises(WarehouseNotFoundError):
            await self.handler.execute(self.command)
        self.locations.get_for_update.assert_not_awaited()
        self.warehouses.get_for_share.return_value = self.warehouse
        self.locations.get_for_update.return_value = None
        with self.assertRaises(StockLocationNotFoundError):
            await self.handler.execute(self.command)
        self.locations.save.assert_not_awaited()

    async def test_invalid_domain_values_do_not_persist_partial_changes(self) -> None:
        """Отказ позднего Domain-метода не сохраняет ранее подготовленный новый код."""
        with self.assertRaises(InventoryError):
            await self.handler.execute(
                replace(
                    self.command,
                    fields=frozenset({"code", "name"}),
                    code="valid",
                    name="\u200bInvalid",
                )
            )
        self.locations.save.assert_not_awaited()
        self.assertEqual(self.location.code.value, "original")

    async def test_missing_row_in_returning_never_becomes_insert(self) -> None:
        """Репозиторий завершает обновление предметной ошибкой при исчезнувшей строке."""
        session = Mock(scalar=AsyncMock(return_value=None), execute=AsyncMock())
        with self.assertRaises(StockLocationNotFoundError):
            await SqlAlchemyStockLocationRepository(session).save(self.location)
        session.scalar.assert_awaited_once()
        session.execute.assert_not_awaited()
