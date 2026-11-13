"""Назначение основной STORAGE через Application и защита write-адаптера."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.modules.inventory.application.warehouse.command.set_default_storage_location.command import (
    SetDefaultStorageLocationCommand,
)
from src.modules.inventory.application.warehouse.command.set_default_storage_location.handler import (
    SetDefaultStorageLocationHandler,
)
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    StockLocationInactiveError,
    StockLocationNotFoundError,
)
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import (
    InvalidDefaultStorageLocationError,
    WarehouseCodeAlreadyExistsError,
    WarehouseNotFoundError,
)
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)


class DriverConstraintError(Exception):
    """Представляет типизированные метаданные ограничения без зависимости от драйвера."""

    def __init__(self, sqlstate: str, constraint_name: str) -> None:
        """Сохраняет SQLSTATE и имя ограничения для проверки перевода ошибок."""
        super().__init__("constraint failure")
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class DefaultStorageApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет координацию портов, Domain-решения и отсутствие частичной записи."""

    async def asyncSetUp(self) -> None:
        """Готовит склад с прежней основной локацией и новый дочерний адрес."""
        warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("main"),
            name=WarehouseNameVO("Основной склад"),
        )
        self.previous = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=warehouse.snapshot(),
            code=LocationCodeVO("storage"),
            name=LocationNameVO("Прежняя основная"),
            location_type=LocationType.STORAGE,
        )
        self.warehouse = warehouse.set_default_storage_location(
            self.previous.snapshot()
        )
        self.location = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            parent=self.previous.snapshot(),
            code=LocationCodeVO("new"),
            name=LocationNameVO("Новая основная"),
            location_type=LocationType.STORAGE,
        )
        self.warehouses = Mock(spec=WarehouseRepositoryProtocol)
        self.warehouses.get_for_update = AsyncMock(return_value=self.warehouse)
        self.warehouses.save = AsyncMock()
        self.locations = Mock(spec=StockLocationRepositoryProtocol)
        self.locations.get_for_update = AsyncMock(return_value=self.location)
        self.handler = SetDefaultStorageLocationHandler(self.warehouses, self.locations)
        self.command = SetDefaultStorageLocationCommand(
            self.warehouse.id, self.location.id
        )

    async def test_assigns_after_ordered_locks_and_preserves_other_state(self) -> None:
        """Сначала блокирует склад, затем его локацию и сохраняет только новый Warehouse."""
        calls = Mock()
        calls.attach_mock(self.warehouses.get_for_update, "warehouse")
        calls.attach_mock(self.locations.get_for_update, "location")
        calls.attach_mock(self.warehouses.save, "save")
        result = await self.handler.execute(self.command)
        self.assertEqual(
            [call[0] for call in calls.mock_calls], ["warehouse", "location", "save"]
        )
        self.warehouses.get_for_update.assert_awaited_once_with(self.warehouse.id)
        self.locations.get_for_update.assert_awaited_once_with(
            self.location.id, warehouse_id=self.warehouse.id
        )
        self.warehouses.save.assert_awaited_once_with(
            self.warehouse.set_default_storage_location(self.location.snapshot())
        )
        self.assertEqual(result.default_storage_location_id, self.location.id.uuid)
        self.assertEqual(
            (result.id, result.code, result.name, result.is_active),
            (self.warehouse.id.uuid, "main", "Основной склад", True),
        )
        self.assertEqual(self.warehouse.default_storage_location_id, self.previous.id)
        self.assertTrue(self.previous.is_active)
        self.assertEqual(self.location.parent_location_id, self.previous.id)
        self.locations.save.assert_not_called()

    async def test_configures_inactive_warehouse_without_activation(self) -> None:
        """Справочная настройка не требует ensure_available и не активирует склад."""
        self.warehouses.get_for_update.return_value = self.warehouse.deactivate()
        result = await self.handler.execute(self.command)
        self.assertFalse(result.is_active)
        self.assertEqual(result.default_storage_location_id, self.location.id.uuid)

    async def test_repeat_reads_and_validates_but_does_not_save(self) -> None:
        """Повторное назначение проверяет актуальную локацию без лишнего UPDATE."""
        self.warehouses.get_for_update.return_value = (
            self.warehouse.set_default_storage_location(self.location.snapshot())
        )
        result = await self.handler.execute(self.command)
        self.assertEqual(result.default_storage_location_id, self.location.id.uuid)
        self.locations.get_for_update.assert_awaited_once()
        self.warehouses.save.assert_not_awaited()
        self.locations.get_for_update.return_value = replace(
            self.location, is_active=False
        )
        with self.assertRaises(StockLocationInactiveError):
            await self.handler.execute(self.command)
        self.warehouses.save.assert_not_awaited()

    async def test_domain_rejects_other_types_and_inactive_location(self) -> None:
        """Бизнес-проверки выполняет существующий Domain; исходная ссылка сохраняется."""
        for kind in LocationType:
            if kind is LocationType.STORAGE:
                continue
            self.locations.get_for_update.return_value = replace(
                self.location, location_type=kind
            )
            with (
                self.subTest(kind=kind),
                self.assertRaises(InvalidDefaultStorageLocationError),
            ):
                await self.handler.execute(self.command)
        self.locations.get_for_update.return_value = self.location.deactivate(
            warehouse=self.warehouse.snapshot()
        )
        with self.assertRaises(StockLocationInactiveError):
            await self.handler.execute(self.command)
        self.warehouses.save.assert_not_awaited()

    async def test_missing_warehouse_short_circuits_location_read(self) -> None:
        """Отсутствие склада не вызывает загрузку адреса и запись."""
        self.warehouses.get_for_update.return_value = None
        with self.assertRaises(WarehouseNotFoundError):
            await self.handler.execute(self.command)
        self.locations.get_for_update.assert_not_awaited()
        self.warehouses.save.assert_not_awaited()

    async def test_missing_or_foreign_location_never_saves(self) -> None:
        """Порт ограничивает адрес складом; отсутствие не меняет основную ссылку."""
        self.locations.get_for_update.return_value = None
        with self.assertRaises(StockLocationNotFoundError):
            await self.handler.execute(self.command)
        self.warehouses.save.assert_not_awaited()

    async def test_write_failure_is_not_reported_as_success(self) -> None:
        """Ошибка записи передаётся внешнему UoW без локального rollback."""
        self.warehouses.save.side_effect = RuntimeError("write unavailable")
        with self.assertRaisesRegex(RuntimeError, "write unavailable"):
            await self.handler.execute(self.command)
        self.assertEqual(self.warehouse.default_storage_location_id, self.previous.id)

    async def test_repository_translates_only_known_constraints_and_keeps_cause(
        self,
    ) -> None:
        """Поддерживает метаданные драйвера, вложенную причину, неизвестные ошибки и orig=None."""
        cases = [
            (
                "23503",
                "fk_warehouses_default_storage_location",
                StockLocationNotFoundError,
            ),
            ("23505", "uq_warehouses_code", WarehouseCodeAlreadyExistsError),
            ("23503", "unknown_fk", IntegrityError),
            ("23505", "fk_warehouses_default_storage_location", IntegrityError),
        ]
        for state, constraint, expected in cases:
            for nested in (False, True):
                driver = DriverConstraintError(state, constraint)
                original = Exception("driver wrapper") if nested else driver
                if nested:
                    original.__cause__ = driver
                error = IntegrityError("UPDATE", {}, original)
                session = Mock(scalar=AsyncMock(side_effect=error))
                with self.subTest(state=state, constraint=constraint, nested=nested):
                    with self.assertRaises(expected) as caught:
                        await SqlAlchemyWarehouseRepository(session).save(
                            self.warehouse
                        )
                    if expected is IntegrityError:
                        self.assertIs(caught.exception, error)
                    else:
                        self.assertIs(caught.exception.__cause__, error)
        error = IntegrityError("UPDATE", {}, None)
        with self.assertRaises(IntegrityError) as caught:
            await SqlAlchemyWarehouseRepository(
                Mock(scalar=AsyncMock(side_effect=error))
            ).save(self.warehouse)
        self.assertIs(caught.exception, error)
