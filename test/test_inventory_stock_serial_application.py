"""Оркестрация Serial, межагрегатные блокировки и перевод известных конфликтов."""

import unittest
from dataclasses import replace
from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from test.test_inventory_packaging_type_application import DriverConstraintError
from src.modules.inventory.application.stock_serial.command.create_stock_serial.command import (
    CreateStockSerialCommand,
)
from src.modules.inventory.application.stock_serial.command.create_stock_serial.handler import (
    CreateStockSerialHandler,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.handler import (
    GetStockSerialHandler,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.query import (
    GetStockSerialQuery,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.handler import (
    ListStockSerialsHandler,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.query import (
    ListStockSerialsQuery,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemInUseError,
    InventoryItemNotFoundError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_serial.error import (
    StockSerialNumberAlreadyExistsError,
    StockSerialNotFoundError,
    SerialTrackingNotAllowedError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.infrastructure.stock_serial.persistence.mapper import (
    StockSerialMapper,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.repository import (
    SqlAlchemyStockSerialRepository,
)


class StockSerialApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет реальные фабрики Domain через наблюдаемые write-порты общей транзакции."""

    def setUp(self) -> None:
        """Готовит серийный SKU, порты и стабильный новый идентификатор."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("S"),
            tracking_mode=TrackingMode.SERIAL,
        )
        self.items = Mock(get_for_update=AsyncMock(return_value=self.item))
        self.lots = Mock(get_for_update=AsyncMock(return_value=None))
        self.serials = Mock(add=AsyncMock())
        self.identifier = uuid4()
        self.handler = CreateStockSerialHandler(
            self.items,
            self.lots,
            self.serials,
            Mock(new=Mock(return_value=self.identifier)),
        )
        self.command = CreateStockSerialCommand(self.item.id, " 000SN-a ")

    async def test_standalone_creation_preserves_number_and_stores_no_dates(
        self,
    ) -> None:
        """Создание SERIAL блокирует только SKU и сохраняет типизированный агрегат без дат."""
        result = await self.handler.execute(self.command)
        self.items.get_for_update.assert_awaited_once_with(self.item.id)
        self.lots.get_for_update.assert_not_awaited()
        serial = self.serials.add.await_args.args[0]
        self.assertEqual(
            (result.id, result.number, result.date_source, result.lot_id),
            (self.identifier, "000SN-a", "NONE", None),
        )
        self.assertEqual(
            set(StockSerialMapper.to_insert_values(serial)),
            {"id", "inventory_item_id", "number", "lot_id"},
        )
        self.assertFalse(hasattr(serial, "dates"))

    async def test_linked_creation_locks_item_before_lot_then_saves(self) -> None:
        """Порядок блокировок совпадает с изменением дат партии; результат использует снимок Lot."""
        item = replace(self.item, tracking_mode=TrackingMode.LOT_AND_SERIAL)
        lot = StockLot.create(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=item.tracking_snapshot(),
            number=LotNumberVO("000L"),
            dates=StockDatesVO(manufactured_on=date(2024, 2, 29)),
        )
        self.items.get_for_update.return_value = item
        self.lots.get_for_update.return_value = lot
        calls = Mock()
        for target, name in (
            (self.items.get_for_update, "item"),
            (self.lots.get_for_update, "lot"),
            (self.serials.add, "add"),
        ):
            calls.attach_mock(target, name)
        result = await self.handler.execute(replace(self.command, lot_id=lot.id))
        self.assertEqual([call[0] for call in calls.mock_calls], ["item", "lot", "add"])
        self.lots.get_for_update.assert_awaited_once_with(
            lot.id, inventory_item_id=item.id
        )
        self.assertEqual(
            (result.date_source, result.lot_id, result.manufactured_on),
            ("LOT", lot.id.uuid, lot.dates.manufactured_on),
        )

    async def test_missing_item_lot_or_incompatible_mode_never_inserts(self) -> None:
        """Ошибки владельца, партии и Domain останавливают запись экземпляра."""
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.items.get_for_update.return_value = self.item
        with self.assertRaises(StockLotNotFoundError):
            await self.handler.execute(
                replace(self.command, lot_id=StockLotIdVO(uuid4()))
            )
        self.items.get_for_update.return_value = replace(
            self.item, tracking_mode=TrackingMode.NONE
        )
        with self.assertRaises(SerialTrackingNotAllowedError):
            await self.handler.execute(self.command)
        self.serials.add.assert_not_awaited()

    async def test_write_error_is_not_success(self) -> None:
        """Handler не скрывает ошибку записи от внешнего UoW."""
        self.serials.add.side_effect = RuntimeError("write failed")
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            await self.handler.execute(self.command)

    async def test_read_handlers_normalize_search_and_scope_missing_resources(
        self,
    ) -> None:
        """Query-порты возвращают проекции, не восстанавливая текущую конфигурацию SKU."""
        repository = Mock(
            item_exists=AsyncMock(return_value=False),
            list=AsyncMock(),
            get_details=AsyncMock(return_value=None),
        )
        with self.assertRaises(InventoryItemNotFoundError):
            await ListStockSerialsHandler(repository).execute(
                ListStockSerialsQuery(self.item.id)
            )
        repository.item_exists.return_value = True
        query = ListStockSerialsQuery(self.item.id, search="  A_% ")
        await ListStockSerialsHandler(repository).execute(query)
        self.assertEqual(repository.list.await_args.args[0].search, "A_%")
        with self.assertRaises(StockSerialNotFoundError):
            await GetStockSerialHandler(repository).execute(
                GetStockSerialQuery(self.item.id, StockSerialIdVO(uuid4()))
            )

    async def test_repository_translates_only_exact_unique_and_preserves_cause(
        self,
    ) -> None:
        """Неизвестные SQLSTATE и ограничения не превращаются в конфликт номера."""
        await self.handler.execute(self.command)
        serial = self.serials.add.await_args.args[0]
        session = Mock(execute=AsyncMock())
        for state, constraint, expected in (
            (
                "23505",
                "uq_stock_serials_item_number",
                StockSerialNumberAlreadyExistsError,
            ),
            ("23503", "uq_stock_serials_item_number", IntegrityError),
            ("23505", "other", IntegrityError),
            (None, None, IntegrityError),
        ):
            error = IntegrityError(
                "insert",
                {},
                DriverConstraintError(state, constraint) if state else None,
            )
            session.execute.side_effect = error
            with self.assertRaises(expected) as caught:
                await SqlAlchemyStockSerialRepository(session).add(serial)
            if expected is StockSerialNumberAlreadyExistsError:
                self.assertIs(caught.exception.__cause__, error)

    async def test_serial_usage_blocks_item_deletion(self) -> None:
        """Standalone Serial защищает SKU и без партий либо связей с Catalog."""
        with self.assertRaises(InventoryItemInUseError):
            self.item.ensure_can_delete(
                InventoryItemDeletionUsage(False, has_stock_serials=True)
            )
