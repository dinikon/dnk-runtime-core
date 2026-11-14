"""Идентичность партий, структурные даты и готовность к будущему поступлению."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.error import (
    ExpirationDateNotAllowedError,
    ExpirationDateRequiredError,
    InvalidStockDatesError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
    InvalidTrackingConfigurationError,
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
from src.modules.inventory.domain.policy.stock_expiration import StockExpirationPolicy
from src.modules.inventory.domain.policy.stock_lot import StockLotPolicy
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import (
    InvalidLotNumberError,
    InvalidStockLotValueError,
    LotTrackingNotAllowedError,
    StockLotItemMismatchError,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockLotValueObjectTests(unittest.TestCase):
    """Проверяет только собственные значения номера, дат и ID партии."""

    def test_number_preserves_case_and_leading_zeros_after_trim(self) -> None:
        """Номер партии нормализует пробелы, сохраняя исходную идентификацию."""
        number = LotNumberVO("  000Lot-a  ")
        self.assertEqual(number.value, "000Lot-a")
        self.assertEqual(number, LotNumberVO("000Lot-a"))
        self.assertNotEqual(number, LotNumberVO("000LOT-A"))
        self.assertEqual(len({number, LotNumberVO("000Lot-a")}), 1)
        with self.assertRaises(FrozenInstanceError):
            number.value = "changed"

    def test_number_rejects_empty_untyped_and_control_values(self) -> None:
        """Запрещает пустой ввод и скрытые управляющие символы, включая края строки."""
        for value in (None, 123, "", "   ", "\tLOT", "LOT\n", "L\x7fOT", "L\u200bOT"):
            with self.subTest(value=value), self.assertRaises(InvalidLotNumberError):
                LotNumberVO(value)

    def test_dates_allow_missing_equal_historical_and_future_values(self) -> None:
        """VO не определяет просрочку и разрешает независимое заполнение двух дат."""
        for manufactured_on, expires_on in (
            (None, None),
            (date(2000, 1, 1), None),
            (None, date(2001, 1, 1)),
            (date(2000, 1, 1), date(2000, 1, 1)),
            (date(2000, 1, 1), date(2001, 1, 1)),
            (date(9998, 1, 1), date(9999, 1, 1)),
        ):
            with self.subTest(manufactured_on=manufactured_on, expires_on=expires_on):
                dates = StockDatesVO(manufactured_on, expires_on)
                self.assertEqual(dates.manufactured_on, manufactured_on)
                self.assertEqual(dates.expires_on, expires_on)
        self.assertEqual(StockDatesVO(), StockDatesVO(None, None))

    def test_dates_reject_time_untyped_values_and_reversed_order(self) -> None:
        """Не превращает datetime и строки в календарные даты и проверяет их порядок."""
        for name in ("manufactured_on", "expires_on"):
            for value in ("2000-01-01", 0, False, datetime(2000, 1, 1), object()):
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(InvalidStockDatesError),
                ):
                    StockDatesVO(**{name: value})
        with self.assertRaises(InvalidStockDatesError):
            StockDatesVO(date(2001, 1, 1), date(2000, 1, 1))
        dates = StockDatesVO(expires_on=date(2000, 1, 1))
        with self.assertRaises(FrozenInstanceError):
            dates.expires_on = None

    def test_identifier_requires_uuid_and_has_separate_identity_type(self) -> None:
        """Идентификаторы партии и товара не взаимозаменяемы даже с одинаковым UUID."""
        value = uuid4()
        self.assertEqual(StockLotIdVO(value).uuid, value)
        self.assertNotEqual(StockLotIdVO(value), InventoryItemIdVO(value))
        with self.assertRaises(EntityIdTypeError):
            StockLotIdVO(str(value))


class StockExpirationPolicyTests(unittest.TestCase):
    """Проверяет заполнение дат отдельно от полноты данных перед поступлением."""

    def test_all_modes_allow_incomplete_dates_but_required_is_not_ready(self) -> None:
        """Производственная дата не заменяет обязательное окончание срока годности."""
        for dates in (StockDatesVO(), StockDatesVO(manufactured_on=date(2000, 1, 1))):
            for mode in ExpirationMode:
                with self.subTest(dates=dates, mode=mode):
                    StockExpirationPolicy.ensure_dates_allowed(
                        dates=dates, expiration_mode=mode
                    )
                    if mode is ExpirationMode.REQUIRED:
                        with self.assertRaises(ExpirationDateRequiredError):
                            StockExpirationPolicy.ensure_ready_for_receipt(
                                dates=dates, expiration_mode=mode
                            )
                    else:
                        StockExpirationPolicy.ensure_ready_for_receipt(
                            dates=dates, expiration_mode=mode
                        )

    def test_none_rejects_expiration_and_optional_does_not_restrict_past_notes(
        self,
    ) -> None:
        """NONE запрещает заполнение срока, OPTIONAL не оценивает прошедшую дату."""
        for expires_on in (date(2000, 1, 1), date(9999, 1, 1)):
            dates = StockDatesVO(expires_on=expires_on)
            for check in (
                StockExpirationPolicy.ensure_dates_allowed,
                StockExpirationPolicy.ensure_ready_for_receipt,
            ):
                with self.subTest(check=check, expires_on=expires_on):
                    with self.assertRaises(ExpirationDateNotAllowedError):
                        check(dates=dates, expiration_mode=ExpirationMode.NONE)
                    check(dates=dates, expiration_mode=ExpirationMode.OPTIONAL)

    def test_required_checks_presence_without_deciding_expired_receipt_rules(
        self,
    ) -> None:
        """Наличие даты и разрешение приёмки просрочки остаются разными проверками."""
        StockExpirationPolicy.ensure_ready_for_receipt(
            dates=StockDatesVO(expires_on=date(2000, 1, 1)),
            expiration_mode=ExpirationMode.REQUIRED,
        )

    def test_policy_requires_typed_dates_and_mode(self) -> None:
        """Чистая Policy отклоняет сырые настройки доменными ошибками."""
        for check in (
            StockExpirationPolicy.ensure_dates_allowed,
            StockExpirationPolicy.ensure_ready_for_receipt,
        ):
            with self.subTest(check=check):
                with self.assertRaises(InvalidStockDatesError):
                    check(dates=None, expiration_mode=ExpirationMode.OPTIONAL)
                with self.assertRaises(InvalidTrackingConfigurationError):
                    check(dates=StockDatesVO(), expiration_mode="OPTIONAL")


class StockLotDomainTests(unittest.TestCase):
    """Проверяет фабрики партии, снимки настроек и неизменяемые переходы."""

    def setUp(self) -> None:
        """Готовит товар с обязательным сроком и пустую карточку партии."""
        self.item = self.make_item()
        self.snapshot = self.item.tracking_snapshot()
        self.lot = self.create_lot()

    def make_item(self, **changes: object) -> InventoryItem:
        """Создаёт реальный агрегат товара с явно заданными настройками."""
        values = dict(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("VITAMINS"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        return InventoryItem.create(**(values | changes))

    def create_lot(self, **changes: object) -> StockLot:
        """Создаёт партию через проверяемый снимок товара."""
        values = dict(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=self.snapshot,
            number=LotNumberVO("000LOT-a"),
            dates=StockDatesVO(),
        )
        return StockLot.create(**(values | changes))

    def restore_lot(self, **changes: object) -> StockLot:
        """Восстанавливает полный собственный состав без снимка текущих настроек."""
        values = dict(
            identifier=self.lot.id,
            inventory_item_id=self.lot.inventory_item_id,
            number=self.lot.number,
            dates=self.lot.dates,
        )
        return StockLot.restore(**(values | changes))

    def test_item_provides_minimal_immutable_tracking_snapshot(self) -> None:
        """Снимок отделён от корня и не включает его упаковки, штрихкоды и SKU."""
        self.assertEqual(
            {field.name for field in fields(self.snapshot)},
            {"inventory_item_id", "tracking_mode", "expiration_mode"},
        )
        self.assertEqual(self.snapshot.inventory_item_id, self.item.id)
        self.assertEqual(self.snapshot.tracking_mode, self.item.tracking_mode)
        self.assertEqual(self.snapshot.expiration_mode, self.item.expiration_mode)
        self.assertEqual(
            self.item.change_sku(SkuVO("OTHER")).tracking_snapshot(), self.snapshot
        )
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.tracking_mode = TrackingMode.NONE

    def test_creation_enforces_tracking_matrix_for_all_valid_item_configurations(
        self,
    ) -> None:
        """Партия создаётся только при LOT и LOT_AND_SERIAL независимо от режима дат."""
        for tracking in TrackingMode:
            for expiration in ExpirationMode:
                if (
                    tracking in (TrackingMode.NONE, TrackingMode.SERIAL)
                    and expiration is ExpirationMode.REQUIRED
                ):
                    continue
                snapshot = self.make_item(
                    tracking_mode=tracking, expiration_mode=expiration
                ).tracking_snapshot()
                with self.subTest(tracking=tracking, expiration=expiration):
                    if tracking in (TrackingMode.LOT, TrackingMode.LOT_AND_SERIAL):
                        lot = self.create_lot(inventory_item=snapshot)
                        self.assertEqual(
                            lot.inventory_item_id, snapshot.inventory_item_id
                        )
                    else:
                        with self.assertRaises(LotTrackingNotAllowedError):
                            self.create_lot(inventory_item=snapshot)

    def test_required_card_can_be_completed_before_receipt_without_mutation(
        self,
    ) -> None:
        """Заполнение срока делает неполную партию готовой, сохраняя исходную карточку."""
        with self.assertRaises(ExpirationDateRequiredError):
            self.lot.ensure_ready_for_receipt(inventory_item=self.snapshot)
        dates = StockDatesVO(date(2000, 1, 1), date(2001, 1, 1))
        completed = self.lot.change_dates(dates, inventory_item=self.snapshot)
        self.assertIsNone(
            completed.ensure_ready_for_receipt(inventory_item=self.snapshot)
        )
        self.assertEqual(
            (completed.id, completed.inventory_item_id, completed.number),
            (self.lot.id, self.item.id, self.lot.number),
        )
        self.assertIs(completed.dates, dates)
        self.assertEqual(self.lot.dates, StockDatesVO())
        self.assertEqual(self.restore_lot(dates=dates), completed)
        incomplete = completed.change_dates(
            StockDatesVO(), inventory_item=self.snapshot
        )
        with self.assertRaises(ExpirationDateRequiredError):
            incomplete.ensure_ready_for_receipt(inventory_item=self.snapshot)
        self.assertEqual(completed.dates, dates)

    def test_none_allows_production_date_but_rejects_expiration_on_create_and_change(
        self,
    ) -> None:
        """Неподходящая дата не попадает в партию и не меняет исходный экземпляр."""
        snapshot = replace(self.snapshot, expiration_mode=ExpirationMode.NONE)
        lot = self.create_lot(
            inventory_item=snapshot,
            dates=StockDatesVO(manufactured_on=date(2000, 1, 1)),
        )
        lot.ensure_ready_for_receipt(inventory_item=snapshot)
        dates = StockDatesVO(expires_on=date(2001, 1, 1))
        with self.assertRaises(ExpirationDateNotAllowedError):
            self.create_lot(inventory_item=snapshot, dates=dates)
        with self.assertRaises(ExpirationDateNotAllowedError):
            lot.change_dates(dates, inventory_item=snapshot)
        self.assertIsNone(lot.dates.expires_on)

    def test_optional_past_note_is_ready_and_remains_a_distinct_mode(self) -> None:
        """Историческая дата в OPTIONAL не мешает прохождению проверки полноты."""
        snapshot = replace(self.snapshot, expiration_mode=ExpirationMode.OPTIONAL)
        dates = StockDatesVO(expires_on=date(2000, 1, 1))
        lot = self.create_lot(inventory_item=snapshot, dates=dates)
        lot.ensure_ready_for_receipt(inventory_item=snapshot)
        self.assertEqual(lot.dates, dates)
        self.assertIs(snapshot.expiration_mode, ExpirationMode.OPTIONAL)

    def test_foreign_item_cannot_change_dates_or_use_lot_for_receipt(self) -> None:
        """Одинаковые настройки разных товаров не делают партии взаимозаменяемыми."""
        foreign = self.make_item().tracking_snapshot()
        with self.assertRaises(StockLotItemMismatchError):
            self.lot.change_dates(
                StockDatesVO(expires_on=date(2001, 1, 1)), inventory_item=foreign
            )
        with self.assertRaises(StockLotItemMismatchError):
            self.lot.ensure_ready_for_receipt(inventory_item=foreign)
        self.assertEqual(self.lot.dates, StockDatesVO())

    def test_restore_preserves_history_and_current_rules_are_checked_on_use(
        self,
    ) -> None:
        """Восстановление истории не обращается к текущему товару и не стирает даты."""
        dates = StockDatesVO(date(2000, 1, 1), date(2001, 1, 1))
        restored = self.restore_lot(dates=dates)
        self.assertIs(restored.id, self.lot.id)
        self.assertIs(restored.inventory_item_id, self.lot.inventory_item_id)
        self.assertIs(restored.number, self.lot.number)
        self.assertIs(restored.dates, dates)
        restored.ensure_ready_for_receipt(inventory_item=self.snapshot)
        with self.assertRaises(ExpirationDateNotAllowedError):
            restored.ensure_ready_for_receipt(
                inventory_item=replace(
                    self.snapshot, expiration_mode=ExpirationMode.NONE
                )
            )
        for mode in (TrackingMode.NONE, TrackingMode.SERIAL):
            with self.subTest(mode=mode), self.assertRaises(LotTrackingNotAllowedError):
                restored.ensure_ready_for_receipt(
                    inventory_item=replace(
                        self.snapshot,
                        tracking_mode=mode,
                        expiration_mode=ExpirationMode.OPTIONAL,
                    )
                )
        self.assertEqual(restored.dates, dates)

    def test_factories_reject_untyped_values_and_foreign_identifier_types(self) -> None:
        """Проверяет обязательные значения через создание и независимое восстановление."""
        for factory in (self.create_lot, self.restore_lot):
            for changes in (
                {"identifier": None},
                {"identifier": self.item.id},
                {"number": "LOT"},
                {"number": None},
                {"dates": None},
                {"dates": {"expires_on": date(2001, 1, 1)}},
            ):
                with (
                    self.subTest(factory=factory, changes=changes),
                    self.assertRaises(InvalidStockLotValueError),
                ):
                    factory(**changes)
        for value in (None, self.lot.id, uuid4()):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockLotValueError),
            ):
                self.restore_lot(inventory_item_id=value)

    def test_malformed_or_aggregate_instead_of_snapshot_is_rejected_at_every_entry(
        self,
    ) -> None:
        """Снимок проверяется потребителем, включая типизированные поля его конструктора."""
        for invalid in (
            None,
            self.item,
            replace(self.snapshot, tracking_mode="LOT"),
            replace(self.snapshot, expiration_mode="REQUIRED"),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
                    self.create_lot(inventory_item=invalid)
                with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
                    self.lot.change_dates(StockDatesVO(), inventory_item=invalid)
                with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
                    self.lot.ensure_ready_for_receipt(inventory_item=invalid)
        with self.assertRaises(InvalidStockLotValueError):
            self.create_lot(
                inventory_item=replace(self.snapshot, inventory_item_id=self.lot.id)
            )
        with self.assertRaises(InvalidInventoryItemTrackingSnapshotError):
            StockLotPolicy.ensure_compatible(
                inventory_item_id=self.item.id,
                inventory_item=replace(self.snapshot, inventory_item_id=self.lot.id),
            )
        with self.assertRaises(InvalidStockLotValueError):
            StockLotPolicy.ensure_compatible(
                inventory_item_id=self.lot.id, inventory_item=self.snapshot
            )

    def test_failed_date_change_and_invalid_direct_state_do_not_bypass_validation(
        self,
    ) -> None:
        """Ошибка значения оставляет исходную партию целой; готовность проверяет собственный состав."""
        with self.assertRaises(InvalidStockLotValueError):
            self.lot.change_dates(None, inventory_item=self.snapshot)
        invalid = StockLot(
            self.lot.id, self.lot.inventory_item_id, "LOT", StockDatesVO()
        )
        with self.assertRaises(InvalidStockLotValueError):
            invalid.ensure_ready_for_receipt(inventory_item=self.snapshot)
        self.assertEqual(self.lot.dates, StockDatesVO())

    def test_lot_is_immutable_and_has_independent_identity_for_the_same_number(
        self,
    ) -> None:
        """Domain не подменяет будущую атомарную уникальность номеров в tenant-хранении."""
        other = self.create_lot(number=self.lot.number)
        self.assertNotEqual(other.id, self.lot.id)
        self.assertEqual(other.inventory_item_id, self.lot.inventory_item_id)
        for obj, name, value in (
            (self.lot, "dates", StockDatesVO()),
            (self.lot, "inventory_item_id", other.inventory_item_id),
            (self.lot, "number", LotNumberVO("OTHER")),
            (self.lot, "id", other.id),
        ):
            with self.subTest(name=name), self.assertRaises(FrozenInstanceError):
                setattr(obj, name, value)
