"""Контракты и оркестрация StockLot без БД, включая перевод только известного UNIQUE."""

from datetime import date
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.modules.inventory.application.stock_lot.command.create_stock_lot.command import (
    CreateStockLotCommand,
)
from src.modules.inventory.application.stock_lot.command.create_stock_lot.handler import (
    CreateStockLotHandler,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.handler import (
    GetStockLotHandler,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.query import (
    GetStockLotQuery,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.handler import (
    ListStockLotsHandler,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.query import (
    ListStockLotsQuery,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemInUseError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_lot.error import (
    StockLotNumberAlreadyExistsError,
    StockLotNotFoundError,
    LotTrackingNotAllowedError,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.infrastructure.stock_lot.persistence.mapper import (
    StockLotMapper,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.repository import (
    SqlAlchemyStockLotRepository,
)

from test.test_inventory_packaging_type_application import DriverConstraintError


class StockLotApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет фактические доменные фабрики и порядок работы с портами."""

    def setUp(self) -> None:
        """Готовит реальный SKU и наблюдаемые write-порты одной транзакции."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("sku"),
            tracking_mode=TrackingMode.LOT,
        )
        self.items = Mock(get_for_update=AsyncMock(return_value=self.item))
        self.lots = Mock(add=AsyncMock())
        self.identifier = uuid4()
        self.handler = CreateStockLotHandler(
            self.items, self.lots, Mock(new=Mock(return_value=self.identifier))
        )
        self.command = CreateStockLotCommand(
            self.item.id, " 000Lot-a ", date(2024, 2, 29)
        )

    async def test_create_locks_owner_calls_domain_and_writes_exact_values(
        self,
    ) -> None:
        """Создание получает снимок под блокировкой, сохраняет доменный ID и date."""
        calls = Mock()
        calls.attach_mock(self.items.get_for_update, "lock")
        calls.attach_mock(self.lots.add, "add")
        result = await self.handler.execute(self.command)
        self.assertEqual([call[0] for call in calls.mock_calls], ["lock", "add"])
        self.items.get_for_update.assert_awaited_once_with(self.item.id)
        self.assertEqual(
            (result.id, result.number, result.manufactured_on),
            (self.identifier, "000Lot-a", date(2024, 2, 29)),
        )
        lot = self.lots.add.await_args.args[0]
        self.assertEqual(
            StockLotMapper.to_insert_values(lot)["inventory_item_id"], self.item.id.uuid
        )
        self.assertEqual(lot.dates.manufactured_on, result.manufactured_on)

    async def test_missing_or_incompatible_item_prevents_insertion(self) -> None:
        """Отсутствующий SKU и запрет Domain не доходят до сохранения партии."""
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.items.get_for_update.return_value = InventoryItem.create(
            identifier=self.item.id, sku=self.item.sku
        )
        with self.assertRaises(LotTrackingNotAllowedError):
            await self.handler.execute(self.command)
        self.lots.add.assert_not_awaited()

    async def test_write_failure_reaches_outer_uow(self) -> None:
        """Handler не выдаёт DTO при отказе записи и не открывает собственный UoW."""
        self.lots.add.side_effect = RuntimeError("write failed")
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            await self.handler.execute(self.command)

    async def test_read_handlers_distinguish_missing_owner_and_normalize_search(
        self,
    ) -> None:
        """Read-side возвращает конкретную проекцию без загрузки Domain-агрегата."""
        repository = Mock(
            item_exists=AsyncMock(return_value=False),
            list=AsyncMock(),
            get_details=AsyncMock(return_value=None),
        )
        query = ListStockLotsQuery(self.item.id, search=" 000Lot-a ")
        handler = ListStockLotsHandler(repository)
        with self.assertRaises(InventoryItemNotFoundError):
            await handler.execute(query)
        repository.list.assert_not_awaited()
        repository.item_exists.return_value = True
        await handler.execute(query)
        self.assertEqual(repository.list.await_args.args[0].search, "000Lot-a")
        with self.assertRaises(StockLotNotFoundError):
            await GetStockLotHandler(repository).execute(
                GetStockLotQuery(self.item.id, StockLotIdVO(uuid4()))
            )

    async def test_repository_only_translates_named_number_unique(self) -> None:
        """Известный UNIQUE сохраняет причину; неизвестные ограничения не маскируются."""
        await self.handler.execute(self.command)
        lot = self.lots.add.await_args.args[0]
        for wrapped in (False, True):
            driver = DriverConstraintError("23505", "uq_stock_lots_item_number")
            original = Exception("wrapper") if wrapped else driver
            if wrapped:
                original.__cause__ = driver
            error = IntegrityError("INSERT", {}, original)
            session = Mock(execute=AsyncMock(side_effect=error))
            with self.assertRaises(StockLotNumberAlreadyExistsError) as caught:
                await SqlAlchemyStockLotRepository(session).add(lot)
            self.assertIs(caught.exception.__cause__, error)
            session.rollback.assert_not_called()
            session.commit.assert_not_called()
        missing = IntegrityError("INSERT", {}, Exception("missing"))
        missing.orig = None
        for error in (
            missing,
            IntegrityError(
                "INSERT",
                {},
                DriverConstraintError("23503", "uq_stock_lots_item_number"),
            ),
            IntegrityError(
                "INSERT", {}, DriverConstraintError("23505", "other_unique")
            ),
        ):
            with self.assertRaises(IntegrityError) as caught:
                await SqlAlchemyStockLotRepository(
                    Mock(execute=AsyncMock(side_effect=error))
                ).add(lot)
            self.assertIs(caught.exception, error)

    async def test_item_deletion_guard_keeps_catalog_and_adds_lots(self) -> None:
        """Новая проверка партий не отменяет прежний запрет использования Catalog."""
        self.item.ensure_can_delete(InventoryItemDeletionUsage(False, False))
        for usage in (
            InventoryItemDeletionUsage(True, False),
            InventoryItemDeletionUsage(False, True),
        ):
            with self.assertRaises(InventoryItemInUseError):
                self.item.ensure_can_delete(usage)
