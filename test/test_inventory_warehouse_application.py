"""Координация склада и основной локации через порты Application."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
)
from src.modules.inventory.application.warehouse.command.create_warehouse.handler import (
    CreateWarehouseHandler,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.handler import (
    GetWarehouseHandler,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.handler import (
    ListWarehousesHandler,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListQueryError,
)
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseCodeError,
    InvalidWarehouseNameError,
    WarehouseNotFoundError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


class WarehouseApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет доменные defaults и последовательность атомарной координации."""

    async def test_creation_prepares_independent_aggregates_and_preserves_ids(
        self,
    ) -> None:
        """Создаёт активные агрегаты и назначает локацию только после её добавления."""
        calls = Mock()
        warehouses = Mock(add=AsyncMock(), save=AsyncMock())
        locations = Mock(add=AsyncMock())
        calls.attach_mock(warehouses.add, "warehouse_add")
        calls.attach_mock(locations.add, "location_add")
        calls.attach_mock(warehouses.save, "warehouse_save")
        warehouse_id, location_id = uuid4(), uuid4()
        handler = CreateWarehouseHandler(
            warehouses,
            locations,
            Mock(new=Mock(side_effect=[warehouse_id, location_id])),
        )
        result = await handler.execute(
            CreateWarehouseCommand(" MAIN ", " Основной склад ")
        )
        initial = warehouses.add.await_args.args[0]
        location = locations.add.await_args.args[0]
        prepared = warehouses.save.await_args.args[0]
        self.assertEqual(
            [call[0] for call in calls.mock_calls],
            ["warehouse_add", "location_add", "warehouse_save"],
        )
        self.assertIsNone(initial.default_storage_location_id)
        self.assertTrue(initial.is_active)
        self.assertEqual(location.warehouse_id, initial.id)
        self.assertEqual(location.location_type, LocationType.STORAGE)
        self.assertIsNone(location.parent_location_id)
        self.assertTrue(location.is_active)
        self.assertEqual(prepared.default_storage_location_id, location.id)
        self.assertEqual(
            (result.id, result.default_storage_location_id), (warehouse_id, location_id)
        )
        self.assertEqual((result.code, result.name), ("main", "Основной склад"))

    async def test_invalid_values_never_write(self) -> None:
        """Ошибки VO возникают до первого сохранения, без частичных вызовов портов."""
        warehouses, locations = Mock(add=AsyncMock(), save=AsyncMock()), Mock(
            add=AsyncMock()
        )
        handler = CreateWarehouseHandler(
            warehouses, locations, Mock(new=Mock(side_effect=uuid4))
        )
        for command, error in (
            (CreateWarehouseCommand(" ", "Name"), InvalidWarehouseCodeError),
            (CreateWarehouseCommand("code", "\u200bname"), InvalidWarehouseNameError),
        ):
            with self.subTest(command=command), self.assertRaises(error):
                await handler.execute(command)
        warehouses.add.assert_not_awaited()
        locations.add.assert_not_awaited()
        warehouses.save.assert_not_awaited()

    async def test_missing_card_is_domain_error(self) -> None:
        """Отсутствие проекции преобразуется в ошибку склада."""
        with self.assertRaises(WarehouseNotFoundError):
            await GetWarehouseHandler(
                Mock(get_details=AsyncMock(return_value=None))
            ).execute(GetWarehouseQuery(WarehouseIdVO(uuid4())))

    async def test_list_checks_transport_independent_parameters(self) -> None:
        """Проверяет пагинацию, типы фильтров и нормализацию пробелов вне HTTP."""
        repository = Mock(list=AsyncMock())
        handler = ListWarehousesHandler(repository)
        query = ListWarehousesQuery(search="  Київ  ", is_active=False)
        await handler.execute(query)
        repository.list.assert_awaited_once_with(replace(query, search="Київ"))
        for changes in (
            {"offset": -1},
            {"offset": True},
            {"limit": 0},
            {"limit": 101},
            {"limit": False},
            {"search": 1},
            {"is_active": 1},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidWarehouseListQueryError),
            ):
                await handler.execute(replace(query, **changes))
        self.assertEqual(repository.list.await_count, 1)
