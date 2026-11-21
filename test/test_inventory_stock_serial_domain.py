import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date
from uuid import uuid4

from src.modules.inventory.domain.inventory_item.error import (
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.policy.stock_tracking_dates import (
    StockTrackingDatesPolicy,
)
from src.modules.inventory.domain.error import ExpirationDateRequiredError
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
)
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
from src.modules.inventory.domain.policy.stock_serial import StockSerialPolicy
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.error import (
    InvalidSerialConfigurationError,
    InvalidSerialNumberError,
    InvalidStockSerialValueError,
    SerialTrackingNotAllowedError,
    StockSerialItemMismatchError,
    StockSerialLotMismatchError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockSerialValueObjectTests(unittest.TestCase):
    """Проверяет собственные значения серийного номера и внутреннего ID экземпляра."""

    def test_number_trims_preserves_identity_and_is_immutable(self) -> None:
        """Сохраняет ведущие нули и регистр, поддерживая равенство и хеширование."""
        number = SerialNumberVO("  000SN-a  ")
        self.assertEqual(number.value, "000SN-a")
        self.assertEqual(number, SerialNumberVO("000SN-a"))
        self.assertNotEqual(number, SerialNumberVO("000SN-A"))
        self.assertEqual(len({number, SerialNumberVO("000SN-a")}), 1)
        with self.assertRaises(FrozenInstanceError):
            number.value = "OTHER"

    def test_number_rejects_empty_untyped_and_control_values(self) -> None:
        """Не принимает пустоту, нестроковый ввод и скрытые управляющие символы."""
        for value in (None, 123, "", "   ", "\tSN", "SN\n", "S\x7fN", "S\u200bN"):
            with self.subTest(value=value), self.assertRaises(InvalidSerialNumberError):
                SerialNumberVO(value)

    def test_identifier_is_separate_and_requires_uuid(self) -> None:
        """Идентификаторы товара, партии и экземпляра не взаимозаменяемы."""
        value = uuid4()
        serial_id = StockSerialIdVO(value)
        self.assertEqual(serial_id.uuid, value)
        self.assertNotEqual(serial_id, InventoryItemIdVO(value))
        self.assertNotEqual(serial_id, StockLotIdVO(value))
        with self.assertRaises(EntityIdTypeError):
            StockSerialIdVO(str(value))


class StockSerialDomainTests(unittest.TestCase):
    """Проверяет идентичность экземпляра и единственный источник дат в партии."""

    def setUp(self) -> None:
        """Готовит самостоятельный серийный товар без контроля срока."""
        self.item = self.make_item()
        self.serial = self.create_serial()

    def make_item(self, **changes: object) -> InventoryItem:
        """Создаёт товар с поштучным учётом и явно выбранными настройками."""
        return InventoryItem.create(
            **(
                dict(
                    identifier=InventoryItemIdVO(uuid4()),
                    sku=SkuVO("DEVICE"),
                    tracking_mode=TrackingMode.SERIAL,
                )
                | changes
            )
        )

    def make_lot(
        self, item: InventoryItem, dates: StockDatesVO = StockDatesVO()
    ) -> StockLot:
        """Создаёт партию только для поддерживающего её товара."""
        return StockLot.create(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=item.tracking_snapshot(),
            number=LotNumberVO("LOT-1"),
            dates=dates,
        )

    def create_serial(self, **changes: object) -> StockSerial:
        """Создаёт экземпляр без собственных дат и без количества."""
        return StockSerial.create(
            **(
                dict(
                    identifier=StockSerialIdVO(uuid4()),
                    inventory_item=self.item.tracking_snapshot(),
                    number=SerialNumberVO("000SN-a"),
                )
                | changes
            )
        )

    def test_tracking_and_expiration_matrix(self) -> None:
        """Разрешает партию только LOT_AND_SERIAL, а обязательный срок только партийным товарам."""
        for mode in TrackingMode:
            for expiration in ExpirationMode:
                with self.subTest(mode=mode, expiration=expiration):
                    if expiration is ExpirationMode.REQUIRED and mode in (
                        TrackingMode.NONE,
                        TrackingMode.SERIAL,
                    ):
                        with self.assertRaises(InvalidTrackingConfigurationError):
                            self.make_item(
                                tracking_mode=mode, expiration_mode=expiration
                            )
                        continue
                    item = self.make_item(
                        tracking_mode=mode, expiration_mode=expiration
                    )
                    lot = StockLot.restore(
                        identifier=StockLotIdVO(uuid4()),
                        inventory_item_id=item.id,
                        number=LotNumberVO("LOT"),
                        dates=StockDatesVO(),
                    ).snapshot()
                    for linked in (False, True):
                        values = dict(
                            inventory_item=item.tracking_snapshot(),
                            lot=lot if linked else None,
                        )
                        if not mode.requires_serial:
                            with self.assertRaises(SerialTrackingNotAllowedError):
                                self.create_serial(**values)
                        elif (mode is TrackingMode.LOT_AND_SERIAL) != linked:
                            with self.assertRaises(InvalidSerialConfigurationError):
                                self.create_serial(**values)
                        else:
                            serial = self.create_serial(**values)
                            self.assertEqual(serial.inventory_item_id, item.id)
                            self.assertEqual(serial.lot_id, lot.id if linked else None)
                            self.assertFalse(hasattr(serial, "dates"))

    def test_restore_keeps_identity_without_current_settings(self) -> None:
        """Восстановление проверяет собственное состояние, не запрашивая текущие настройки."""
        for lot_id in (None, StockLotIdVO(uuid4())):
            serial = StockSerial.restore(
                identifier=self.serial.id,
                inventory_item_id=self.item.id,
                number=self.serial.number,
                lot_id=lot_id,
            )
            self.assertEqual(serial.id, self.serial.id)
            self.assertEqual(serial.lot_id, lot_id)
            self.assertEqual(serial.number.value, "000SN-a")

    def test_identity_and_snapshot_have_no_dates_or_date_methods(self) -> None:
        """Контракт экземпляра не предоставляет хранение, изменение или готовность собственных дат."""
        self.assertEqual(
            set(self.serial.__dataclass_fields__),
            {"id", "inventory_item_id", "number", "lot_id"},
        )
        self.assertEqual(
            set(self.serial.snapshot().__dataclass_fields__),
            {"id", "inventory_item_id", "lot_id"},
        )
        for name in (
            "dates",
            "change_dates",
            "ensure_ready_for_receipt",
            "execution_snapshot",
            "availability_snapshot",
        ):
            self.assertFalse(hasattr(self.serial, name))
        for name in self.serial.__dataclass_fields__:
            with self.assertRaises(FrozenInstanceError):
                setattr(self.serial, name, None)

    def test_number_preserves_case_and_leading_zeroes(self) -> None:
        """Разные регистры номера остаются разными значениями одного SKU."""
        self.assertNotEqual(self.serial.number, SerialNumberVO("000SN-A"))
        self.assertEqual(self.serial.number.value, "000SN-a")

    def test_foreign_item_is_rejected(self) -> None:
        """Политика не позволяет использовать экземпляр другого SKU."""
        with self.assertRaises(StockSerialItemMismatchError):
            StockSerialPolicy.ensure_compatible(
                inventory_item_id=self.item.id,
                inventory_item=self.make_item().tracking_snapshot(),
                lot_id=None,
            )

    def test_foreign_lot_and_wrong_lot_id_are_rejected(self) -> None:
        """Партия должна совпасть со ссылкой и принадлежать тому же товару."""
        item = self.make_item(tracking_mode=TrackingMode.LOT_AND_SERIAL)
        lot = self.make_lot(item).snapshot()
        with self.assertRaises(StockSerialLotMismatchError):
            StockSerialPolicy.ensure_compatible(
                inventory_item_id=item.id,
                inventory_item=item.tracking_snapshot(),
                lot_id=StockLotIdVO(uuid4()),
                lot=lot,
            )
        with self.assertRaises(StockSerialLotMismatchError):
            self.create_serial(
                inventory_item=item.tracking_snapshot(),
                lot=replace(lot, inventory_item_id=self.item.id),
            )

    def test_missing_and_malformed_lot_are_rejected(self) -> None:
        """Политика требует снимок партии, фабрика отклоняет произвольные объекты."""
        item = self.make_item(tracking_mode=TrackingMode.LOT_AND_SERIAL)
        for lot in (None, "LOT"):
            with self.assertRaises(InvalidStockLotSnapshotError):
                StockSerialPolicy.ensure_compatible(
                    inventory_item_id=item.id,
                    inventory_item=item.tracking_snapshot(),
                    lot_id=StockLotIdVO(uuid4()),
                    lot=lot,
                )
        with self.assertRaises(InvalidStockLotSnapshotError):
            self.create_serial(lot="LOT")

    def test_invalid_own_values_are_rejected(self) -> None:
        """Восстановление и выдача снимка повторно проверяют собственные типы."""
        values = dict(
            identifier=self.serial.id,
            inventory_item_id=self.item.id,
            number=self.serial.number,
            lot_id=None,
        )
        for changes in (
            dict(identifier=uuid4()),
            dict(inventory_item_id=self.serial.id),
            dict(number="SN"),
            dict(lot_id="LOT"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockSerialValueError),
            ):
                StockSerial.restore(**(values | changes))
        with self.assertRaises(InvalidStockSerialValueError):
            replace(self.serial, number="SN").snapshot()

    def test_malformed_item_snapshot_is_rejected(self) -> None:
        """Создание не принимает агрегат вместо снимка настроек."""
        with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
            self.create_serial(inventory_item=self.item)

    def test_lot_is_only_date_source_and_fresh_snapshot_changes_result(self) -> None:
        """Даты меняются через партию без изменения экземпляра и копирования дат в него."""
        item = self.make_item(
            tracking_mode=TrackingMode.LOT_AND_SERIAL,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        lot = self.make_lot(item)
        serial = self.create_serial(
            inventory_item=item.tracking_snapshot(), lot=lot.snapshot()
        )
        before = serial.snapshot()
        with self.assertRaises(ExpirationDateRequiredError):
            lot.ensure_ready_for_receipt(inventory_item=item.tracking_snapshot())
        dates = StockDatesVO(date(2026, 1, 1), date(2027, 1, 1))
        changed = lot.change_dates(dates, inventory_item=item.tracking_snapshot())
        changed.ensure_ready_for_receipt(inventory_item=item.tracking_snapshot())
        for source in (lot, changed):
            resolved = StockTrackingDatesPolicy.resolve(
                inventory_item=item.tracking_snapshot(),
                lot_id=source.id,
                lot=source.snapshot(),
                serial=serial.snapshot(),
            )
            self.assertEqual(resolved, source.dates)
        self.assertEqual(serial.snapshot(), before)

    def test_standalone_serial_has_no_date_source(self) -> None:
        """Отсутствие партии возвращается как None, а не фиктивные пустые даты."""
        self.assertIsNone(
            StockTrackingDatesPolicy.resolve(
                inventory_item=self.item.tracking_snapshot(),
                lot_id=None,
                lot=None,
                serial=self.serial.snapshot(),
            )
        )

    def test_policy_rejects_invalid_identifiers(self) -> None:
        """Политика проверяет типы ID даже при ручном вызове."""
        for item_id, lot_id in ((uuid4(), None), (self.item.id, "LOT")):
            with self.assertRaises(InvalidStockSerialValueError):
                StockSerialPolicy.ensure_compatible(
                    inventory_item_id=item_id,
                    inventory_item=self.item.tracking_snapshot(),
                    lot_id=lot_id,
                )
