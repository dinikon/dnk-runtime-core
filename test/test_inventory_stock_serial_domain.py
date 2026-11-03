"""Серийные экземпляры, источники дат и совместимость со снимками товара и партии."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.error import (
    ExpirationDateNotAllowedError,
    ExpirationDateRequiredError,
)
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
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
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
    """Проверяет самостоятельный и партийный режим через публичное поведение агрегата."""

    def setUp(self) -> None:
        """Готовит серийный товар с обязательным сроком и неполный экземпляр."""
        self.item = self.make_item()
        self.snapshot = self.item.tracking_snapshot()
        self.serial = self.create_serial()

    def make_item(self, **changes: object) -> InventoryItem:
        """Создаёт товар с корректной единицей и шагом серийного учёта."""
        values = dict(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("DEVICE"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.SERIAL,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        return InventoryItem.create(**(values | changes))

    def make_lot(
        self, item: InventoryItem, dates: StockDatesVO = StockDatesVO()
    ) -> StockLot:
        """Восстанавливает партию независимо от текущих настроек товара для проверок совместимости."""
        return StockLot.restore(
            identifier=StockLotIdVO(uuid4()),
            inventory_item_id=item.id,
            number=LotNumberVO("LOT-1"),
            dates=dates,
        )

    def create_serial(self, **changes: object) -> StockSerial:
        """Создаёт самостоятельный экземпляр с явно переопределёнными параметрами."""
        values = dict(
            identifier=StockSerialIdVO(uuid4()),
            inventory_item=self.snapshot,
            number=SerialNumberVO("000SN-a"),
            dates=StockDatesVO(),
            lot=None,
        )
        return StockSerial.create(**(values | changes))

    def restore_serial(
        self, serial: StockSerial | None = None, **changes: object
    ) -> StockSerial:
        """Восстанавливает полный собственный состав без текущих снимков."""
        original = self.serial if serial is None else serial
        values = dict(
            identifier=original.id,
            inventory_item_id=original.inventory_item_id,
            number=original.number,
            lot_id=original.lot_id,
            dates=original.dates,
        )
        return StockSerial.restore(**(values | changes))

    def test_creation_enforces_tracking_mode_and_date_source_matrix(self) -> None:
        """Разрешает свои даты только SERIAL и партию только LOT_AND_SERIAL."""
        for mode in TrackingMode:
            for expiration in ExpirationMode:
                if mode is TrackingMode.NONE and expiration is ExpirationMode.REQUIRED:
                    continue
                item = self.make_item(tracking_mode=mode, expiration_mode=expiration)
                lot = self.make_lot(item).snapshot()
                for backed_by_lot in (False, True):
                    with self.subTest(
                        mode=mode, expiration=expiration, backed_by_lot=backed_by_lot
                    ):
                        values = dict(
                            inventory_item=item.tracking_snapshot(),
                            dates=None if backed_by_lot else StockDatesVO(),
                            lot=lot if backed_by_lot else None,
                        )
                        if mode in (TrackingMode.NONE, TrackingMode.LOT):
                            with self.assertRaises(SerialTrackingNotAllowedError):
                                self.create_serial(**values)
                        elif (mode is TrackingMode.LOT_AND_SERIAL) != backed_by_lot:
                            with self.assertRaises(InvalidSerialConfigurationError):
                                self.create_serial(**values)
                        else:
                            serial = self.create_serial(**values)
                            self.assertEqual(serial.inventory_item_id, item.id)
                            self.assertEqual(
                                serial.lot_id, lot.id if backed_by_lot else None
                            )
                            self.assertEqual(self.restore_serial(serial), serial)

    def test_expiration_modes_use_the_selected_source_for_creation_and_readiness(
        self,
    ) -> None:
        """NONE запрещает срок, OPTIONAL допускает заметку, REQUIRED требует дату до поступления."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            for expiration in ExpirationMode:
                item = self.make_item(tracking_mode=mode, expiration_mode=expiration)
                snapshot = item.tracking_snapshot()
                for dates in (
                    StockDatesVO(),
                    StockDatesVO(expires_on=date(2001, 1, 1)),
                ):
                    lot = (
                        self.make_lot(item, dates).snapshot()
                        if mode is TrackingMode.LOT_AND_SERIAL
                        else None
                    )
                    values = dict(
                        inventory_item=snapshot,
                        dates=dates if lot is None else None,
                        lot=lot,
                    )
                    with self.subTest(mode=mode, expiration=expiration, dates=dates):
                        if (
                            expiration is ExpirationMode.NONE
                            and dates.expires_on is not None
                        ):
                            with self.assertRaises(ExpirationDateNotAllowedError):
                                self.create_serial(**values)
                        else:
                            serial = self.create_serial(**values)
                            if (
                                expiration is ExpirationMode.REQUIRED
                                and dates.expires_on is None
                            ):
                                with self.assertRaises(ExpirationDateRequiredError):
                                    serial.ensure_ready_for_receipt(
                                        inventory_item=snapshot, lot=lot
                                    )
                            else:
                                serial.ensure_ready_for_receipt(
                                    inventory_item=snapshot, lot=lot
                                )

    def test_required_individual_dates_can_be_completed_without_changing_identity(
        self,
    ) -> None:
        """Заполнение и очистка дат возвращают новый экземпляр с прежними идентификаторами."""
        with self.assertRaises(ExpirationDateRequiredError):
            self.serial.ensure_ready_for_receipt(inventory_item=self.snapshot)
        dates = StockDatesVO(date(2000, 1, 1), date(2001, 1, 1))
        completed = self.serial.change_dates(dates, inventory_item=self.snapshot)
        completed.ensure_ready_for_receipt(inventory_item=self.snapshot)
        self.assertEqual(
            (
                completed.id,
                completed.inventory_item_id,
                completed.number,
                completed.lot_id,
            ),
            (self.serial.id, self.item.id, self.serial.number, None),
        )
        self.assertIs(completed.dates, dates)
        self.assertEqual(self.serial.dates, StockDatesVO())
        incomplete = completed.change_dates(
            StockDatesVO(), inventory_item=self.snapshot
        )
        with self.assertRaises(ExpirationDateRequiredError):
            incomplete.ensure_ready_for_receipt(inventory_item=self.snapshot)
        self.assertEqual(completed.dates, dates)

    def test_lot_dates_are_resolved_from_fresh_snapshot_without_copying(self) -> None:
        """Изменение партии отражается через новый снимок, а экземпляр не хранит копию дат."""
        item = self.make_item(tracking_mode=TrackingMode.LOT_AND_SERIAL)
        snapshot = item.tracking_snapshot()
        lot = self.make_lot(item)
        before = lot.snapshot()
        serial = self.create_serial(inventory_item=snapshot, lot=before, dates=None)
        with self.assertRaises(ExpirationDateRequiredError):
            serial.ensure_ready_for_receipt(inventory_item=snapshot, lot=before)
        changed = lot.change_dates(
            StockDatesVO(expires_on=date(2001, 1, 1)), inventory_item=snapshot
        )
        serial.ensure_ready_for_receipt(inventory_item=snapshot, lot=changed.snapshot())
        self.assertIsNone(serial.dates)
        self.assertEqual(serial.lot_id, lot.id)
        self.assertEqual(before.dates, StockDatesVO())
        self.assertEqual(lot.dates, StockDatesVO())
        with self.assertRaises(ExpirationDateRequiredError):
            serial.ensure_ready_for_receipt(inventory_item=snapshot, lot=before)
        with self.assertRaises(FrozenInstanceError):
            before.dates = changed.dates

    def test_lot_backed_serial_cannot_edit_dates_or_implicitly_detach_lot(self) -> None:
        """Даты партии изменяются через её корень, сохраняя связь и состояние экземпляра."""
        item = self.make_item(tracking_mode=TrackingMode.LOT_AND_SERIAL)
        lot = self.make_lot(item).snapshot()
        serial = self.create_serial(
            inventory_item=item.tracking_snapshot(), lot=lot, dates=None
        )
        with self.assertRaises(InvalidSerialConfigurationError):
            serial.change_dates(StockDatesVO(), inventory_item=item.tracking_snapshot())
        with self.assertRaises(InvalidSerialConfigurationError):
            serial.change_dates(
                StockDatesVO(),
                inventory_item=replace(
                    item.tracking_snapshot(), tracking_mode=TrackingMode.SERIAL
                ),
            )
        self.assertEqual(serial.lot_id, lot.id)
        self.assertIsNone(serial.dates)

    def test_foreign_item_cannot_change_or_use_existing_serial(self) -> None:
        """Настройки другого товара не разрешают изменение или поступление экземпляра."""
        foreign = self.make_item().tracking_snapshot()
        with self.assertRaises(StockSerialItemMismatchError):
            self.serial.change_dates(StockDatesVO(), inventory_item=foreign)
        with self.assertRaises(StockSerialItemMismatchError):
            self.serial.ensure_ready_for_receipt(inventory_item=foreign)
        self.assertEqual(self.serial.dates, StockDatesVO())

    def test_linked_lot_must_match_both_lot_id_and_inventory_item(self) -> None:
        """Чужая партия и другой товар отклоняются независимо от совпадения остальных данных."""
        item = self.make_item(tracking_mode=TrackingMode.LOT_AND_SERIAL)
        snapshot = item.tracking_snapshot()
        lot = self.make_lot(item).snapshot()
        serial = self.create_serial(inventory_item=snapshot, lot=lot, dates=None)
        for invalid in (
            replace(lot, id=StockLotIdVO(uuid4())),
            replace(lot, inventory_item_id=self.item.id),
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(StockSerialLotMismatchError),
            ):
                serial.ensure_ready_for_receipt(inventory_item=snapshot, lot=invalid)
        with self.assertRaises(StockSerialLotMismatchError):
            self.create_serial(
                inventory_item=snapshot,
                lot=self.make_lot(self.item).snapshot(),
                dates=None,
            )

    def test_linked_lot_snapshot_is_required_and_rejects_untyped_fields(self) -> None:
        """Потребитель проверяет снимок, включая его собственные ID и тип дат."""
        item = self.make_item(tracking_mode=TrackingMode.LOT_AND_SERIAL)
        snapshot = item.tracking_snapshot()
        lot = self.make_lot(item)
        valid = lot.snapshot()
        serial = self.create_serial(inventory_item=snapshot, lot=valid, dates=None)
        for invalid in (
            None,
            lot,
            replace(valid, id=self.item.id),
            replace(valid, inventory_item_id=valid.id),
            replace(valid, dates=None),
            replace(valid, dates={}),
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidStockLotSnapshotError),
            ):
                serial.ensure_ready_for_receipt(inventory_item=snapshot, lot=invalid)
        with self.assertRaises(InvalidStockLotSnapshotError):
            self.create_serial(inventory_item=snapshot, lot=lot, dates=None)

    def test_standalone_serial_rejects_unexpected_lot_snapshot(self) -> None:
        """Партия не игнорируется в режиме SERIAL и не подменяет собственные даты."""
        lot = self.make_lot(self.item).snapshot()
        with self.assertRaises(InvalidSerialConfigurationError):
            self.serial.ensure_ready_for_receipt(inventory_item=self.snapshot, lot=lot)
        with self.assertRaises(InvalidSerialConfigurationError):
            self.create_serial(lot=lot, dates=None)

    def test_restore_checks_exclusive_date_source_without_current_snapshots(
        self,
    ) -> None:
        """История восстанавливается без текущих связей, но два источника или их отсутствие запрещены."""
        dates = StockDatesVO(expires_on=date(2001, 1, 1))
        standalone = self.restore_serial(dates=dates)
        self.assertIs(standalone.id, self.serial.id)
        self.assertIs(standalone.number, self.serial.number)
        self.assertIs(standalone.dates, dates)
        lot_id = StockLotIdVO(uuid4())
        linked = self.restore_serial(lot_id=lot_id, dates=None)
        self.assertIs(linked.lot_id, lot_id)
        for changes in (
            dict(lot_id=None, dates=None),
            dict(lot_id=lot_id, dates=dates),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSerialConfigurationError),
            ):
                self.restore_serial(**changes)
        with self.assertRaises(InvalidSerialConfigurationError):
            self.create_serial(dates=None)
        with self.assertRaises(InvalidSerialConfigurationError):
            self.create_serial(lot=self.make_lot(self.item).snapshot())

    def test_current_tracking_and_expiration_are_checked_on_use_after_restore(
        self,
    ) -> None:
        """Восстановленная карточка не получает права поступления при несовместимых текущих настройках."""
        serial = self.restore_serial(dates=StockDatesVO(expires_on=date(2001, 1, 1)))
        for mode in (TrackingMode.NONE, TrackingMode.LOT):
            with (
                self.subTest(mode=mode),
                self.assertRaises(SerialTrackingNotAllowedError),
            ):
                serial.ensure_ready_for_receipt(
                    inventory_item=replace(self.snapshot, tracking_mode=mode)
                )
        with self.assertRaises(InvalidSerialConfigurationError):
            serial.ensure_ready_for_receipt(
                inventory_item=replace(
                    self.snapshot, tracking_mode=TrackingMode.LOT_AND_SERIAL
                )
            )
        with self.assertRaises(ExpirationDateNotAllowedError):
            serial.ensure_ready_for_receipt(
                inventory_item=replace(
                    self.snapshot, expiration_mode=ExpirationMode.NONE
                )
            )
        self.assertEqual(serial.dates.expires_on, date(2001, 1, 1))

    def test_factories_reject_untyped_values_and_foreign_id_classes(self) -> None:
        """Явные фабрики проверяют типы идентификаторов, номера и собственного источника дат."""
        for factory in (self.create_serial, self.restore_serial):
            for changes in (
                dict(identifier=None),
                dict(identifier=self.item.id),
                dict(identifier=StockLotIdVO(uuid4())),
                dict(number="SN"),
                dict(number=LotNumberVO("LOT")),
                dict(dates={}),
            ):
                with (
                    self.subTest(factory=factory, changes=changes),
                    self.assertRaises(InvalidStockSerialValueError),
                ):
                    factory(**changes)
        for changes in (
            dict(inventory_item_id=self.serial.id),
            dict(lot_id=self.item.id, dates=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockSerialValueError),
            ):
                self.restore_serial(**changes)

    def test_malformed_item_snapshots_are_domain_errors(self) -> None:
        """Корень товара и сырые поля снимка не принимаются вместо корректного контракта."""
        for invalid in (
            None,
            self.item,
            replace(self.snapshot, tracking_mode="SERIAL"),
            replace(self.snapshot, expiration_mode="REQUIRED"),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
                    self.create_serial(inventory_item=invalid)
                with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
                    self.serial.change_dates(StockDatesVO(), inventory_item=invalid)
                with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
                    self.serial.ensure_ready_for_receipt(inventory_item=invalid)
        with self.assertRaises(InvalidStockSerialValueError):
            self.create_serial(
                inventory_item=replace(self.snapshot, inventory_item_id=self.serial.id)
            )
        with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
            self.serial.ensure_ready_for_receipt(
                inventory_item=replace(self.snapshot, inventory_item_id=self.serial.id)
            )

    def test_invalid_date_changes_and_direct_state_do_not_bypass_validation(
        self,
    ) -> None:
        """Ошибки не изменяют исходный экземпляр, а прямой конструктор не обходит проверку готовности."""
        with self.assertRaises(InvalidStockSerialValueError):
            self.serial.change_dates({}, inventory_item=self.snapshot)
        with self.assertRaises(InvalidSerialConfigurationError):
            self.serial.change_dates(None, inventory_item=self.snapshot)
        invalid = StockSerial(self.serial.id, self.item.id, "SN", None, StockDatesVO())
        with self.assertRaises(InvalidStockSerialValueError):
            invalid.ensure_ready_for_receipt(inventory_item=self.snapshot)
        self.assertEqual(self.serial.dates, StockDatesVO())

    def test_serial_identity_and_source_are_immutable(self) -> None:
        """Данные нельзя менять в обход доменных методов; разные карточки имеют разные ID."""
        other = self.create_serial()
        self.assertNotEqual(self.serial.id, other.id)
        for name, value in (
            ("id", other.id),
            ("inventory_item_id", self.make_item().id),
            ("number", SerialNumberVO("OTHER")),
            ("lot_id", StockLotIdVO(uuid4())),
            ("dates", StockDatesVO()),
        ):
            with self.subTest(name=name), self.assertRaises(FrozenInstanceError):
                setattr(self.serial, name, value)

    def test_policy_returns_the_selected_dates_and_validates_own_input_types(
        self,
    ) -> None:
        """Чистая Policy возвращает проверенный источник и отклоняет сырые собственные значения."""
        values = dict(
            inventory_item_id=self.item.id,
            inventory_item=self.snapshot,
            lot_id=None,
            dates=self.serial.dates,
        )
        self.assertIs(StockSerialPolicy.resolve_dates(**values), self.serial.dates)
        for changes in (
            dict(inventory_item_id=self.serial.id),
            dict(lot_id="LOT"),
            dict(dates="DATE"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockSerialValueError),
            ):
                StockSerialPolicy.resolve_dates(**(values | changes))
