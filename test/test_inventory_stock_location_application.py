"""Сценарии локаций и перевод известных ошибок хранения без HTTP и PostgreSQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.modules.inventory.application.stock_location.command.create_stock_location.command import (
    CreateStockLocationCommand,
)
from src.modules.inventory.application.stock_location.command.create_stock_location.handler import (
    CreateStockLocationHandler,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.handler import (
    GetStockLocationHandler,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.query import (
    GetStockLocationQuery,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.handler import (
    ListStockLocationsHandler,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.query import (
    ListStockLocationsQuery,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    ListStockLocationsResultDTO,
)
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    StockLocationNotFoundError,
    StockLocationCodeAlreadyExistsError,
    StockLocationWarehouseMismatchError,
    InvalidLocationCodeError,
)
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
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)


class StockLocationApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет координацию самостоятельных агрегатов через типизированные порты."""

    async def asyncSetUp(self) -> None:
        """Готовит активный склад, родителя и наблюдаемые write-порты."""
        self.warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("main"),
            name=WarehouseNameVO("Main"),
        )
        self.parent = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("parent"),
            name=LocationNameVO("Parent"),
            location_type=LocationType.STORAGE,
        )
        self.warehouses = Mock(
            get_for_share=AsyncMock(return_value=self.warehouse), save=AsyncMock()
        )
        self.locations = Mock(get=AsyncMock(return_value=self.parent), add=AsyncMock())
        self.location_id = uuid4()
        self.ids = Mock(new=Mock(return_value=self.location_id))
        self.handler = CreateStockLocationHandler(
            self.warehouses, self.locations, self.ids
        )
        self.command = CreateStockLocationCommand(
            self.warehouse.id, " Straße-001 ", " Location ", LocationType.STORAGE
        )

    async def test_root_creation_uses_domain_defaults_and_does_not_assign_default(
        self,
    ) -> None:
        """Канонизирует код, создаёт активную корневую локацию и не сохраняет склад."""
        result = await self.handler.execute(self.command)
        self.assertEqual(
            (result.id, result.warehouse_id, result.parent_location_id),
            (self.location_id, self.warehouse.id.uuid, None),
        )
        self.assertEqual(
            (result.code, result.name, result.is_active),
            ("strasse-001", "Location", True),
        )
        self.warehouses.get_for_share.assert_awaited_once_with(self.warehouse.id)
        self.locations.get.assert_not_awaited()
        self.locations.add.assert_awaited_once()
        self.warehouses.save.assert_not_awaited()
        self.assertIsNone(self.warehouse.default_storage_location_id)

    async def test_inactive_parent_is_valid_and_all_existing_types_are_supported(
        self,
    ) -> None:
        """Domain допускает неактивного родителя как структурную ссылку без наследования."""
        self.locations.get.return_value = self.parent.deactivate(
            warehouse=self.warehouse.snapshot()
        )
        for location_type in LocationType:
            with self.subTest(location_type=location_type):
                result = await self.handler.execute(
                    replace(
                        self.command,
                        location_type=location_type,
                        parent_location_id=self.parent.id,
                    )
                )
                self.assertEqual(result.parent_location_id, self.parent.id.uuid)
                self.assertEqual(result.location_type, location_type)
                self.assertTrue(result.is_active)

    async def test_missing_references_do_not_write(self) -> None:
        """Отсутствующие склад и родитель дают разные предметные ошибки до INSERT."""
        self.warehouses.get_for_share.return_value = None
        with self.assertRaises(WarehouseNotFoundError):
            await self.handler.execute(self.command)
        self.locations.get.assert_not_awaited()
        self.warehouses.get_for_share.return_value = self.warehouse
        self.locations.get.return_value = None
        with self.assertRaises(StockLocationNotFoundError):
            await self.handler.execute(
                replace(self.command, parent_location_id=self.parent.id)
            )
        self.locations.add.assert_not_awaited()

    async def test_domain_rejections_do_not_write(self) -> None:
        """Склад должен быть активен, родитель принадлежать ему, а код быть допустимым."""
        self.warehouses.get_for_share.return_value = self.warehouse.deactivate()
        with self.assertRaises(WarehouseInactiveError):
            await self.handler.execute(self.command)
        self.warehouses.get_for_share.return_value = self.warehouse
        self.locations.get.return_value = replace(
            self.parent, warehouse_id=WarehouseIdVO(uuid4())
        )
        with self.assertRaises(StockLocationWarehouseMismatchError):
            await self.handler.execute(
                replace(self.command, parent_location_id=self.parent.id)
            )
        with self.assertRaises(InvalidLocationCodeError):
            await self.handler.execute(replace(self.command, code=" "))
        self.locations.add.assert_not_awaited()

    async def test_read_handlers_use_projections_and_distinguish_empty_from_missing(
        self,
    ) -> None:
        """Нормализует поиск без проверки структуры команды и не загружает Domain для чтения."""
        empty = ListStockLocationsResultDTO((), 0, 0, 50)
        repository = Mock(
            warehouse_exists=AsyncMock(return_value=True),
            list=AsyncMock(return_value=empty),
            get_details=AsyncMock(return_value=None),
        )
        query = ListStockLocationsQuery(
            self.warehouse.id, search="  Київ  ", is_active=False
        )
        result = await ListStockLocationsHandler(repository).execute(query)
        self.assertIs(result, empty)
        repository.list.assert_awaited_once_with(replace(query, search="Київ"))
        repository.warehouse_exists.return_value = False
        with self.assertRaises(WarehouseNotFoundError):
            await ListStockLocationsHandler(repository).execute(query)
        self.assertEqual(repository.list.await_count, 1)
        with self.assertRaises(StockLocationNotFoundError):
            await GetStockLocationHandler(repository).execute(
                GetStockLocationQuery(self.warehouse.id, self.parent.id)
            )

    async def test_write_adapter_translates_only_known_constraints_with_cause(
        self,
    ) -> None:
        """Известные UNIQUE/FK становятся предметными ошибками; неизвестные пробрасываются."""
        for state, constraint, expected in (
            (
                "23505",
                "uq_stock_locations_warehouse_code",
                StockLocationCodeAlreadyExistsError,
            ),
            ("23503", "fk_stock_locations_warehouse", WarehouseNotFoundError),
            ("23503", "fk_stock_locations_parent", StockLocationNotFoundError),
            ("23505", "unknown", IntegrityError),
            ("23514", "ck_stock_locations_type", IntegrityError),
        ):
            for nested in (False, True):
                with self.subTest(state=state, constraint=constraint, nested=nested):
                    driver = RuntimeError("driver")
                    driver.sqlstate = state
                    driver.constraint_name = constraint
                    original = RuntimeError("adapter") if nested else driver
                    if nested:
                        original.__cause__ = driver
                    failure = IntegrityError("insert", {}, original)
                    repository = SqlAlchemyStockLocationRepository(
                        Mock(execute=AsyncMock(side_effect=failure))
                    )
                    with self.assertRaises(expected) as caught:
                        await repository.add(self.parent)
                    self.assertIs(
                        (
                            caught.exception
                            if expected is IntegrityError
                            else caught.exception.__cause__
                        ),
                        failure,
                    )
        failure = IntegrityError("insert", {}, None)
        with self.assertRaises(IntegrityError) as caught:
            await SqlAlchemyStockLocationRepository(
                Mock(execute=AsyncMock(side_effect=failure))
            ).add(self.parent)
        self.assertIs(caught.exception, failure)
