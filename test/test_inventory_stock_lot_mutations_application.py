"""Обновление дат партии: порядок блокировок, Domain, no-op и типизированная запись."""

from datetime import date
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.application.stock_lot.command.update_stock_lot.command import (
    UpdateStockLotCommand,
)
from src.modules.inventory.application.stock_lot.command.update_stock_lot.handler import (
    UpdateStockLotHandler,
)
from src.modules.inventory.domain.error import ExpirationDateRequiredError
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_tracking_dates import (
    StockTrackingDatesPolicy,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import (
    StockLotNotFoundError,
    LotTrackingNotAllowedError,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.mapper import (
    StockLotMapper,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.repository import (
    SqlAlchemyStockLotRepository,
)


class StockLotMutationsApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет взаимодействие с реальной фабрикой Domain через наблюдаемые порты."""

    def setUp(self) -> None:
        """Создаёт SKU с REQUIRED и партию с датами для обновления и очистки."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("sku"),
            tracking_mode=TrackingMode.LOT_AND_SERIAL,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        self.lot = StockLot.create(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=self.item.tracking_snapshot(),
            number=LotNumberVO("000Lot-a"),
            dates=StockDatesVO(date(2020, 1, 1), date(2030, 1, 1)),
        )
        self.items = Mock(get_for_update=AsyncMock(return_value=self.item))
        self.lots = Mock(
            get_for_update=AsyncMock(return_value=self.lot), save=AsyncMock()
        )
        self.handler = UpdateStockLotHandler(self.items, self.lots)
        self.command = UpdateStockLotCommand(
            self.item.id, self.lot.id, frozenset({"expires_on"}), expires_on=None
        )

    async def test_lock_order_domain_clearing_and_immutable_identity(self) -> None:
        """SKU блокируется до партии; handler сохраняет новый экземпляр без изменения номера."""
        calls = Mock()
        calls.attach_mock(self.items.get_for_update, "item")
        calls.attach_mock(self.lots.get_for_update, "lot")
        calls.attach_mock(self.lots.save, "save")
        result = await self.handler.execute(self.command)
        self.assertEqual(
            [call[0] for call in calls.mock_calls], ["item", "lot", "save"]
        )
        self.lots.get_for_update.assert_awaited_once_with(
            self.lot.id, inventory_item_id=self.item.id
        )
        changed = self.lots.save.await_args.args[0]
        self.assertIsNot(changed, self.lot)
        self.assertEqual(
            (changed.id, changed.inventory_item_id, changed.number),
            (self.lot.id, self.lot.inventory_item_id, self.lot.number),
        )
        self.assertEqual(changed.dates, StockDatesVO(date(2020, 1, 1), None))
        self.assertEqual(self.lot.dates.expires_on, date(2030, 1, 1))
        self.assertIsNone(result.expires_on)

    async def test_missing_item_or_lot_prevents_save(self) -> None:
        """404 возникает до записи, отсутствие владельца не обращается к партиям."""
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.lots.get_for_update.assert_not_awaited()
        self.items.get_for_update.return_value = self.item
        self.lots.get_for_update.return_value = None
        with self.assertRaises(StockLotNotFoundError):
            await self.handler.execute(self.command)
        self.lots.save.assert_not_awaited()

    async def test_noop_skips_write_but_checks_current_tracking(self) -> None:
        """Совпадение дат не обходит актуальную политику Domain."""
        command = UpdateStockLotCommand(
            self.item.id,
            self.lot.id,
            frozenset({"expires_on"}),
            expires_on=self.lot.dates.expires_on,
        )
        result = await self.handler.execute(command)
        self.assertEqual(result.expires_on, self.lot.dates.expires_on)
        self.lots.save.assert_not_awaited()
        self.items.get_for_update.return_value = InventoryItem.create(
            identifier=self.item.id, sku=self.item.sku
        )
        with self.assertRaises(LotTrackingNotAllowedError):
            await self.handler.execute(command)
        self.lots.save.assert_not_awaited()

    async def test_write_error_is_not_success(self) -> None:
        """Handler передаёт технический отказ внешнему UoW без успешного DTO."""
        self.lots.save.side_effect = RuntimeError("write failed")
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            await self.handler.execute(self.command)

    async def test_mapper_restore_and_save_touch_only_dates_with_returning(
        self,
    ) -> None:
        """Repository не меняет номер/владельца, не делает upsert или локальный commit."""
        model = StockLotModel(**StockLotMapper.to_insert_values(self.lot))
        restored = StockLotMapper.to_domain(model)
        self.assertEqual(restored, self.lot)
        self.assertEqual(
            set(StockLotMapper.to_update_values(restored)),
            {"manufactured_on", "expires_on"},
        )
        session = Mock(scalar=AsyncMock(return_value=self.lot.id.uuid))
        await SqlAlchemyStockLotRepository(session).save(self.lot)
        statement = session.scalar.await_args.args[0]
        self.assertIn("RETURNING", str(statement))
        self.assertNotIn("number=", str(statement))
        self.assertNotIn("inventory_item_id=", str(statement))
        self.assertEqual(
            set(statement.compile().params.values()),
            {self.lot.id.uuid, self.item.id.uuid, date(2020, 1, 1), date(2030, 1, 1)},
        )
        session.commit.assert_not_called()
        session.rollback.assert_not_called()
        session.scalar.return_value = None
        with self.assertRaises(StockLotNotFoundError):
            await SqlAlchemyStockLotRepository(session).save(self.lot)

    async def test_serial_resolves_new_lot_snapshot_without_date_copy(self) -> None:
        """Серия использует свежие даты партии; REQUIRED остаётся проверкой готовности к поступлению."""
        serial = StockSerial.create(
            identifier=StockSerialIdVO(uuid4()),
            inventory_item=self.item.tracking_snapshot(),
            number=SerialNumberVO("000S"),
            lot=self.lot.snapshot(),
        )
        self.lot.ensure_ready_for_receipt(inventory_item=self.item.tracking_snapshot())
        await self.handler.execute(self.command)
        changed = self.lots.save.await_args.args[0]
        effective = StockTrackingDatesPolicy.resolve(
            inventory_item=self.item.tracking_snapshot(),
            lot_id=serial.lot_id,
            serial=serial.snapshot(),
            lot=changed.snapshot(),
        )
        self.assertEqual(effective, changed.dates)
        self.assertFalse(hasattr(serial, "dates"))
        with self.assertRaises(ExpirationDateRequiredError):
            changed.ensure_ready_for_receipt(
                inventory_item=self.item.tracking_snapshot()
            )
