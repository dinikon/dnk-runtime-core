"""Изменение идентификации Serial: Domain, порядок блокировок и ошибки хранения."""

import unittest
from dataclasses import replace
from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from test import test_inventory_stock_serial_application as fixture
from test.test_inventory_packaging_type_application import DriverConstraintError
from src.modules.inventory.application.stock_serial.command.update_stock_serial.command import (
    UpdateStockSerialCommand,
)
from src.modules.inventory.application.stock_serial.command.update_stock_serial.handler import (
    UpdateStockSerialHandler,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.error import (
    InvalidSerialConfigurationError,
    InvalidSerialNumberError,
    StockSerialNotFoundError,
    StockSerialNumberAlreadyExistsError,
    SerialTrackingNotAllowedError,
    StockSerialLotMismatchError,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.infrastructure.stock_serial.persistence.mapper import (
    StockSerialMapper,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.repository import (
    SqlAlchemyStockSerialRepository,
)


class StockSerialMutationsApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Использует реальные агрегаты и наблюдаемые порты внешнего UoW."""

    def setUp(self) -> None:
        """Готовит standalone экземпляр и контракт изменения только номера."""
        f = fixture.StockSerialApplicationTests()
        f.setUp()
        self.item = f.item
        self.serial = StockSerial.create(
            identifier=fixture.StockSerialIdVO(uuid4()),
            inventory_item=self.item.tracking_snapshot(),
            number=SerialNumberVO("000S-a"),
        )
        self.items = Mock(get_for_update=AsyncMock(return_value=self.item))
        self.serials = Mock(
            get_for_update=AsyncMock(return_value=self.serial), save=AsyncMock()
        )
        self.lots = Mock(get_for_update=AsyncMock(return_value=None))
        self.handler = UpdateStockSerialHandler(self.items, self.lots, self.serials)
        self.command = UpdateStockSerialCommand(
            self.item.id, self.serial.id, frozenset({"number"}), number=" 000S-A "
        )

    def lot(self, item: fixture.InventoryItem) -> StockLot:
        """Создаёт самостоятельную партию с календарными датами."""
        return StockLot.create(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=item.tracking_snapshot(),
            number=LotNumberVO("L"),
            dates=StockDatesVO(manufactured_on=date(2024, 2, 29)),
        )

    async def test_number_change_preserves_identity_and_other_fields(self) -> None:
        """Номер меняется через Domain без нового ID, SKU и собственных дат."""
        result = await self.handler.execute(self.command)
        saved = self.serials.save.await_args.args[0]
        self.assertEqual(
            (saved.id, saved.inventory_item_id, saved.number.value, saved.lot_id),
            (self.serial.id, self.item.id, "000S-A", None),
        )
        self.assertEqual((result.date_source, result.manufactured_on), ("NONE", None))
        self.lots.get_for_update.assert_not_awaited()
        self.assertEqual(
            set(StockSerialMapper.to_update_values(saved)), {"number", "lot_id"}
        )

    async def test_party_change_locks_in_order_and_keeps_omitted_number(self) -> None:
        """PATCH партии не меняет номер; блокировки идут SKU, Serial, Lot, save."""
        item = replace(self.item, tracking_mode=TrackingMode.LOT_AND_SERIAL)
        first, second = self.lot(item), self.lot(item)
        serial = self.serial.change_identification(
            self.serial.number,
            inventory_item=item.tracking_snapshot(),
            lot=first.snapshot(),
        )
        self.items.get_for_update.return_value = item
        self.serials.get_for_update.return_value = serial
        self.lots.get_for_update.return_value = second
        calls = Mock()
        for method, name in (
            (self.items.get_for_update, "item"),
            (self.serials.get_for_update, "serial"),
            (self.lots.get_for_update, "lot"),
            (self.serials.save, "save"),
        ):
            calls.attach_mock(method, name)
        result = await self.handler.execute(
            replace(self.command, fields=frozenset({"lot_id"}), lot_id=second.id)
        )
        self.assertEqual(
            [call[0] for call in calls.mock_calls], ["item", "serial", "lot", "save"]
        )
        self.assertEqual(
            (result.number, result.lot_id, result.manufactured_on),
            (serial.number.value, second.id.uuid, second.dates.manufactured_on),
        )
        self.serials.get_for_update.assert_awaited_once_with(
            serial.id, inventory_item_id=item.id
        )
        self.lots.get_for_update.assert_awaited_once_with(
            second.id, inventory_item_id=item.id
        )

    async def test_number_only_resolves_existing_party_and_noop_still_validates(
        self,
    ) -> None:
        """Даже при неизменённой связи читается актуальная партия; no-op не пишет."""
        item = replace(self.item, tracking_mode=TrackingMode.LOT_AND_SERIAL)
        lot = self.lot(item)
        serial = self.serial.change_identification(
            self.serial.number,
            inventory_item=item.tracking_snapshot(),
            lot=lot.snapshot(),
        )
        self.items.get_for_update.return_value = item
        self.serials.get_for_update.return_value = serial
        self.lots.get_for_update.return_value = lot
        await self.handler.execute(replace(self.command, number=serial.number.value))
        self.serials.save.assert_not_awaited()
        self.lots.get_for_update.assert_awaited_once()
        self.items.get_for_update.return_value = replace(
            item, tracking_mode=TrackingMode.NONE
        )
        with self.assertRaises(SerialTrackingNotAllowedError):
            await self.handler.execute(
                replace(self.command, number=serial.number.value)
            )

    async def test_missing_resources_stop_writes(self) -> None:
        """Отсутствие владельца, экземпляра или целевой партии не выдаёт успех."""
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.items.get_for_update.return_value = self.item
        self.serials.get_for_update.return_value = None
        with self.assertRaises(StockSerialNotFoundError):
            await self.handler.execute(self.command)
        self.serials.get_for_update.return_value = self.serial
        with self.assertRaises(StockLotNotFoundError):
            await self.handler.execute(
                replace(
                    self.command,
                    fields=frozenset({"lot_id"}),
                    lot_id=StockLotIdVO(uuid4()),
                )
            )
        self.serials.save.assert_not_awaited()

    async def test_domain_rejects_invalid_final_state_without_mutating_original(
        self,
    ) -> None:
        """Чужая партия, пустой номер и несерийный режим сохраняют исходное состояние."""
        linked = replace(self.item, tracking_mode=TrackingMode.LOT_AND_SERIAL)
        original = self.serial.snapshot()
        for action, error in (
            (
                lambda: self.serial.change_identification(
                    SerialNumberVO(""),
                    inventory_item=self.item.tracking_snapshot(),
                    lot=None,
                ),
                InvalidSerialNumberError,
            ),
            (
                lambda: self.serial.change_identification(
                    self.serial.number,
                    inventory_item=linked.tracking_snapshot(),
                    lot=None,
                ),
                InvalidSerialConfigurationError,
            ),
            (
                lambda: self.serial.change_identification(
                    self.serial.number,
                    inventory_item=linked.tracking_snapshot(),
                    lot=replace(
                        self.lot(linked).snapshot(),
                        inventory_item_id=fixture.InventoryItemIdVO(uuid4()),
                    ),
                ),
                StockSerialLotMismatchError,
            ),
        ):
            with self.assertRaises(error):
                action()
            self.assertEqual(self.serial.snapshot(), original)

    async def test_save_checks_missing_row_and_translates_only_known_unique(
        self,
    ) -> None:
        """RETURNING различает отсутствие; unknown ошибки не маскируются конфликтом номера."""
        session = Mock(scalar=AsyncMock(return_value=None))
        with self.assertRaises(StockSerialNotFoundError):
            await SqlAlchemyStockSerialRepository(session).save(self.serial)
        for state, constraint, error_type in (
            (
                "23505",
                "uq_stock_serials_item_number",
                StockSerialNumberAlreadyExistsError,
            ),
            ("23503", "uq_stock_serials_item_number", IntegrityError),
            ("23505", "other", IntegrityError),
        ):
            error = IntegrityError(
                "update", {}, DriverConstraintError(state, constraint)
            )
            session.scalar.side_effect = error
            with self.assertRaises(error_type) as caught:
                await SqlAlchemyStockSerialRepository(session).save(self.serial)
            if error_type is StockSerialNumberAlreadyExistsError:
                self.assertIs(caught.exception.__cause__, error)
        session.commit.assert_not_called()
        session.rollback.assert_not_called()

    async def test_write_failure_reaches_outer_uow(self) -> None:
        """Handler не подтверждает сохранение при отказе репозитория."""
        self.serials.save.side_effect = RuntimeError("save failed")
        with self.assertRaisesRegex(RuntimeError, "save failed"):
            await self.handler.execute(self.command)
