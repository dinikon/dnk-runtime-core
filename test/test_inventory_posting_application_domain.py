"""Применение записи Ledger к конкретной физической позиции по ожидаемой версии."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.error import (
    NegativeStockQuantityError,
    QuantityConversionMismatchError,
    QuantityStepError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockPositionValueError,
    StockDimensionsMismatchError,
    StockPositionUomMismatchError,
    StockPositionVersionConflictError,
    StockPostingPositionMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockLedgerEntryError,
    InvalidStockLedgerEntrySnapshotError,
    ZeroStockLedgerDeltaError,
)
from src.modules.inventory.domain.stock_posting.ledger_entry_snapshot import (
    StockLedgerEntrySnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class PostingApplicationDomainTests(unittest.TestCase):
    """Проверяет адресность записи, версии и существующие инварианты физического количества."""

    def setUp(self) -> None:
        """Готовит две физические позиции одного товара и владельца с разными версиями."""
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.location_a = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.warehouse.id, LocationType.STORAGE, True
        )
        self.location_b = replace(self.location_a, id=StockLocationIdVO(uuid4()))
        self.owner = StockOwnerIdVO(uuid4())
        self.prepare()
        self.time = datetime(2026, 11, 4, 12, tzinfo=UTC)

    def prepare(self, mode: TrackingMode = TrackingMode.NONE) -> None:
        """Создаёт реальные справочники прослеживаемости и исторические физические позиции."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO("PCS" if mode.requires_serial else "KG"),
            quantity_rules=QuantityRulesVO(
                Decimal(1) if mode.requires_serial else Decimal("0.05")
            ),
            tracking_mode=mode,
        )
        self.lot = (
            StockLot.restore(
                identifier=StockLotIdVO(uuid4()),
                inventory_item_id=self.item.id,
                number=LotNumberVO("LOT"),
                dates=StockDatesVO(),
            )
            if mode in (TrackingMode.LOT, TrackingMode.LOT_AND_SERIAL)
            else None
        )
        self.serial = (
            StockSerial.restore(
                identifier=StockSerialIdVO(uuid4()),
                inventory_item_id=self.item.id,
                number=SerialNumberVO("SN"),
                lot_id=self.lot.id if self.lot else None,
            )
            if mode.requires_serial
            else None
        )
        dimensions = StockDimensionsVO(
            self.item.id,
            self.location_a.id,
            self.owner,
            self.lot.id if self.lot else None,
            self.serial.id if self.serial else None,
            StockStatus.SELLABLE,
        )
        self.a = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=dimensions,
            base_uom=self.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(1) if mode.requires_serial else Decimal(10)),
            version=7,
        )
        self.b = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=replace(dimensions, location_id=self.location_b.id),
            base_uom=self.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(0)),
            version=2,
        )

    def entry(
        self, delta: str = "4", position: StockPosition | None = None
    ) -> StockLedgerEntry:
        """Создаёт запись в базовой единице с явным ненулевым направлением."""
        target = self.a if position is None else position
        value = Decimal(delta)
        return StockLedgerEntry.create(
            identifier=StockLedgerEntryIdVO(uuid4()),
            position_id=target.id,
            quantity_delta=StockDeltaVO(value),
            base_uom=target.base_uom,
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(value.copy_abs()), target.base_uom, Decimal(1)
            ),
        )

    def context(self, position: StockPosition) -> dict[str, object]:
        """Возвращает текущие снимки товара, адреса, склада, партии и серии выбранной позиции."""
        location = (
            self.location_a
            if position.dimensions.location_id == self.location_a.id
            else self.location_b
        )
        return dict(
            inventory_item=self.item.stock_snapshot(),
            location=location,
            warehouse=self.warehouse,
            lot=self.lot.snapshot() if self.lot else None,
            serial=self.serial.snapshot() if self.serial else None,
        )

    def apply(
        self, reference: StockPosition | None = None, **changes: object
    ) -> StockPosition:
        """Применяет снимок записи к явно выбранному текущему состоянию и версии."""
        position = self.a if reference is None else reference
        return position.apply_posting_entry(
            **(
                dict(
                    entry=self.entry(position=position).snapshot(),
                    expected_version=position.version,
                )
                | self.context(position)
                | changes
            )
        )

    def posting(
        self,
        kind: StockOperationType,
        entries: tuple[StockLedgerEntry, ...],
        positions: tuple[StockPosition, ...],
    ) -> StockPosting:
        """Фиксирует журнал через существующий корень без изменения переданных позиций."""
        return StockPosting.create(
            identifier=StockPostingIdVO(uuid4()),
            source=PostingSourceVO(StockExecutionIdVO(uuid4())),
            operation_type=kind,
            posted_at=self.time,
            entries=entries,
            inventory_items=(self.item.tracking_snapshot(),),
            lots=(self.lot.snapshot(),) if self.lot else (),
            serials=(self.serial.snapshot(),) if self.serial else (),
            positions=tuple(position.snapshot() for position in positions),
            locations=(
                (self.location_a, self.location_b)
                if kind is StockOperationType.INTERNAL_MOVE
                else ()
            ),
        )

    def test_snapshot_is_minimal_typed_immutable_and_preserves_identity(self) -> None:
        """Геттер возвращает только нужный позиции контракт, сохраняя ссылку на запись и дельту."""
        entry = self.entry()
        snapshot = entry.snapshot()
        self.assertIsInstance(snapshot, StockLedgerEntrySnapshot)
        self.assertEqual(
            set(snapshot.__dataclass_fields__),
            {"id", "position_id", "quantity_delta", "base_uom"},
        )
        for name in ("id", "position_id", "quantity_delta", "base_uom"):
            self.assertIs(getattr(snapshot, name), getattr(entry, name))
        snapshot.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            snapshot.quantity_delta = StockDeltaVO(Decimal(5))

    def test_snapshot_getter_checks_full_original_entity(self) -> None:
        """Сокращённый контракт не позволяет пропустить проверку сохранённого пересчёта Entity."""
        entry = self.entry()
        with self.assertRaises(InvalidStockLedgerEntryError):
            replace(entry, id=uuid4()).snapshot()
        with self.assertRaises(QuantityConversionMismatchError):
            replace(entry, quantity_delta=StockDeltaVO(Decimal(5))).snapshot()

    def test_receipt_and_issue_return_new_correct_position_versions(self) -> None:
        """Обычные движения изменяют только количество и версию соответствующей позиции."""
        for kind, delta, expected in (
            (StockOperationType.RECEIPT, "4", "14"),
            (StockOperationType.ISSUE, "-4", "6"),
        ):
            entry = self.entry(delta)
            posting = self.posting(kind, (entry,), (self.a,))
            changed = self.apply(entry=posting.entries[0].snapshot())
            self.assertEqual(changed.on_hand_qty.value, Decimal(expected))
            self.assertEqual(changed.version, 8)
            self.assertIs(changed.id, self.a.id)
            self.assertIs(changed.dimensions, self.a.dimensions)
            self.assertIs(changed.base_uom, self.a.base_uom)
            self.assertEqual(
                (self.a.on_hand_qty.value, self.a.version), (Decimal(10), 7)
            )

    def test_move_applies_each_target_entry_by_its_own_expected_version(self) -> None:
        """Записи A:-4/B:+4 дают A=6/v8 и B=4/v3 без изменения исходных объектов."""
        outgoing = self.entry("-4", self.a)
        incoming = self.entry("4", self.b)
        posting = self.posting(
            StockOperationType.INTERNAL_MOVE, (outgoing, incoming), (self.a, self.b)
        )
        changed_a = self.apply(
            self.a, entry=posting.entries[0].snapshot(), expected_version=7
        )
        changed_b = self.apply(
            self.b, entry=posting.entries[1].snapshot(), expected_version=2
        )
        self.assertEqual(
            (changed_a.on_hand_qty.value, changed_a.version), (Decimal(6), 8)
        )
        self.assertEqual(
            (changed_b.on_hand_qty.value, changed_b.version), (Decimal(4), 3)
        )
        self.assertEqual(
            (self.a.on_hand_qty.value, self.b.on_hand_qty.value),
            (Decimal(10), Decimal(0)),
        )

    def test_other_position_id_is_rejected_even_for_identical_dimensions(self) -> None:
        """Наличие того же товара и полного ключа не разрешает применить запись к другому ID."""
        other = replace(self.a, id=StockPositionIdVO(uuid4()))
        with self.assertRaises(StockPostingPositionMismatchError):
            self.apply(other, entry=self.entry().snapshot())
        with self.assertRaises(StockPostingPositionMismatchError):
            self.apply(self.b, entry=self.entry().snapshot())
        self.assertEqual(other.on_hand_qty.value, Decimal(10))

    def test_entry_unit_must_match_position_without_implicit_conversion(self) -> None:
        """Число 4 в G или L не становится четырьмя KG из-за выбранного контекста позиции."""
        for uom in ("G", "L", "PCS"):
            entry = replace(self.entry().snapshot(), base_uom=UomCodeVO(uom))
            with (
                self.subTest(uom=uom),
                self.assertRaises(StockPositionUomMismatchError),
            ):
                self.apply(entry=entry)

    def test_expected_version_is_strict_nonnegative_int(self) -> None:
        """Не принимает bool, Decimal, строку, None и отрицательную ожидаемую версию."""
        for value in (True, False, None, "7", Decimal(7), 7.0, -1):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockPositionValueError),
            ):
                self.apply(expected_version=value)

    def test_stale_or_future_version_is_rejected_before_arithmetic(self) -> None:
        """Невалидная версия не запускает расчёт и не создаёт новое состояние позиции."""
        with patch.object(
            StockPosition,
            "apply_delta",
            side_effect=RuntimeError("Не применять дельту"),
        ):
            for version in (0, 6, 8, 100):
                with (
                    self.subTest(version=version),
                    self.assertRaises(StockPositionVersionConflictError),
                ):
                    self.apply(expected_version=version)
        self.assertEqual(self.a.version, 7)

    def test_reusing_old_expected_version_fails_after_success(self) -> None:
        """После первого перехода исходная версия больше не подходит к новому состоянию."""
        entry = self.entry().snapshot()
        changed = self.apply(entry=entry, expected_version=7)
        with self.assertRaises(StockPositionVersionConflictError):
            self.apply(changed, entry=entry, expected_version=7)
        self.assertEqual((changed.on_hand_qty.value, changed.version), (Decimal(14), 8))

    def test_current_version_does_not_replace_global_entry_idempotency(self) -> None:
        """Корень не хранит историю ID записей: глобальный запрет повтора нужен будущему хранению."""
        entry = self.entry().snapshot()
        changed = self.apply(entry=entry)
        repeated = self.apply(changed, entry=entry, expected_version=changed.version)
        self.assertEqual(
            (repeated.on_hand_qty.value, repeated.version), (Decimal(18), 9)
        )

    def test_consumer_rejects_raw_snapshot_values_entity_and_delta(self) -> None:
        """Метод не принимает Entity, число или произвольный объект вместо специализированного снимка."""
        entry = self.entry()
        for value in (None, entry, entry.quantity_delta, Decimal(4), {}):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockLedgerEntrySnapshotError),
            ):
                self.apply(entry=value)
        snapshot = entry.snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(position_id=uuid4()),
            dict(quantity_delta=Decimal(4)),
            dict(base_uom="KG"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockLedgerEntrySnapshotError),
            ):
                self.apply(entry=replace(snapshot, **changes))
        with self.assertRaises(UnknownUomError):
            self.apply(entry=replace(snapshot, base_uom=UomCodeVO("BOX")))

    def test_zero_snapshot_delta_is_forbidden_but_raw_delta_still_allows_zero(
        self,
    ) -> None:
        """Инвариант записи не меняет общий контракт нулевого StockDeltaVO."""
        for value in ("0", "-0.000"):
            snapshot = replace(
                self.entry().snapshot(), quantity_delta=StockDeltaVO(Decimal(value))
            )
            with (
                self.subTest(value=value),
                self.assertRaises(ZeroStockLedgerDeltaError),
            ):
                self.apply(entry=snapshot)
        self.assertIs(
            self.a.apply_delta(StockDeltaVO(Decimal(0)), **self.context(self.a)), self.a
        )

    def test_negative_balance_and_nonmultiple_delta_are_rejected(self) -> None:
        """Новый метод повторно использует существующие правила остатка и шага количества."""
        for value, error in (
            ("-11", NegativeStockQuantityError),
            ("0.03", QuantityStepError),
            ("-0.03", QuantityStepError),
        ):
            with self.subTest(value=value), self.assertRaises(error):
                self.apply(entry=self.entry(value).snapshot())
        invalid_legacy = replace(self.a, on_hand_qty=QuantityVO(Decimal("1.23")))
        with self.assertRaises(QuantityStepError):
            self.apply(invalid_legacy, entry=self.entry("0.02").snapshot())

    def test_context_and_current_item_unit_are_revalidated(self) -> None:
        """Правильная запись не отменяет проверки товара, склада, адреса и текущей единицы."""
        for changes in (
            dict(
                inventory_item=replace(
                    self.item.stock_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                )
            ),
            dict(location=self.location_b),
            dict(warehouse=replace(self.warehouse, id=WarehouseIdVO(uuid4()))),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(StockDimensionsMismatchError),
            ):
                self.apply(**changes)
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.apply(inventory_item=self.item)
        with self.assertRaises(StockPositionUomMismatchError):
            self.apply(
                inventory_item=replace(
                    self.item.stock_snapshot(), base_uom=UomCodeVO("G")
                )
            )

    def test_tracking_modes_and_serial_zero_one_boundaries(self) -> None:
        """Все режимы используют прежний контекст, а серийный экземпляр не получает остаток 2 или дробь."""
        for mode in TrackingMode:
            self.prepare(mode)
            amount = "1" if mode.requires_serial else "4"
            outgoing = self.entry("-" + amount, self.a)
            incoming = self.entry(amount, self.b)
            changed_a = self.apply(self.a, entry=outgoing.snapshot())
            changed_b = self.apply(self.b, entry=incoming.snapshot())
            self.assertEqual(changed_b.on_hand_qty.value, Decimal(amount))
            if mode.requires_serial:
                self.assertEqual(changed_a.on_hand_qty.value, Decimal(0))
                with self.assertRaises(InvalidSerialStockQuantityError):
                    self.apply(entry=self.entry("1").snapshot())
                with self.assertRaises(QuantityStepError):
                    self.apply(entry=self.entry("0.5").snapshot())
                with self.assertRaises(NegativeStockQuantityError):
                    self.apply(self.b, entry=self.entry("-1", self.b).snapshot())

    def test_compensating_entry_restores_quantity_with_another_version(self) -> None:
        """Компенсация применяет противоположный факт через тот же проверенный метод."""
        original = self.posting(
            StockOperationType.ISSUE, (self.entry("-4"),), (self.a,)
        )
        issued = self.apply(entry=original.entries[0].snapshot())
        compensation = StockPosting.create_reversal(
            identifier=StockPostingIdVO(uuid4()),
            source=PostingSourceVO(StockExecutionIdVO(uuid4())),
            posted_at=self.time + timedelta(minutes=1),
            original=original.snapshot(),
            entry_ids=(StockLedgerEntryIdVO(uuid4()),),
            positions=(issued.snapshot(),),
        )
        restored = self.apply(issued, entry=compensation.entries[0].snapshot())
        self.assertEqual(
            (restored.on_hand_qty.value, restored.version), (Decimal(10), 9)
        )
        self.assertEqual(original.entries[0].quantity_delta.value, Decimal(-4))

    def test_failure_of_one_move_side_leaves_all_original_positions_unchanged(
        self,
    ) -> None:
        """Подготовленный кандидат одной стороны не является сохранением пакета при отказе другой."""
        outgoing = self.entry("-11", self.a)
        incoming = self.entry("11", self.b)
        posting = self.posting(
            StockOperationType.INTERNAL_MOVE, (outgoing, incoming), (self.a, self.b)
        )
        candidate_b = self.apply(self.b, entry=posting.entries[1].snapshot())
        with self.assertRaises(NegativeStockQuantityError):
            self.apply(self.a, entry=posting.entries[0].snapshot())
        self.assertEqual(
            (candidate_b.on_hand_qty.value, candidate_b.version), (Decimal(11), 3)
        )
        self.assertEqual((self.a.on_hand_qty.value, self.a.version), (Decimal(10), 7))
        self.assertEqual((self.b.on_hand_qty.value, self.b.version), (Decimal(0), 2))

    def test_historical_conversion_is_preserved_and_not_required_by_position(
        self,
    ) -> None:
        """Геттер проверяет сохранённое равенство, а позиция использует уже рассчитанную базовую дельту."""
        entry = StockLedgerEntry.restore(
            identifier=StockLedgerEntryIdVO(uuid4()),
            position_id=self.a.id,
            quantity_delta=StockDeltaVO(Decimal(5)),
            base_uom=self.a.base_uom,
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(2500)), UomCodeVO("G"), Decimal("0.002")
            ),
        )
        changed = self.apply(entry=entry.snapshot())
        self.assertEqual(changed.on_hand_qty.value, Decimal(15))
        self.assertEqual(entry.conversion.factor_to_base, Decimal("0.002"))
        self.assertEqual(entry.conversion.quantity.value, Decimal(2500))

    def test_hostile_decimal_context_does_not_round_or_change_global_flags(
        self,
    ) -> None:
        """Применение записи наследует точную арифметику без изменения контекста вызывающего кода."""
        position = replace(
            self.a, on_hand_qty=QuantityVO(Decimal("12345678901234567890.10"))
        )
        snapshot = self.entry("0.05").snapshot()
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            changed = self.apply(position, entry=snapshot)
            self.assertEqual(
                changed.on_hand_qty.value, Decimal("12345678901234567890.15")
            )
            self.assertEqual(changed.version, 8)
            self.assertFalse(any(context.flags.values()))

    def test_invalid_direct_position_cannot_bypass_public_method_checks(self) -> None:
        """Прямой dataclass-конструктор не обходит собственные инварианты агрегата."""
        for changes in (
            dict(version=True),
            dict(version=-1),
            dict(on_hand_qty=Decimal(10)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockPositionValueError),
            ):
                self.apply(replace(self.a, **changes), expected_version=7)

    def test_version_zero_is_valid_and_snapshot_and_original_position_stay_immutable(
        self,
    ) -> None:
        """Начальная версия допустима, и успешный переход не изменяет источник записи или позиции."""
        position = replace(self.a, version=0)
        entry = self.entry().snapshot()
        changed = self.apply(position, entry=entry, expected_version=0)
        self.assertEqual(changed.version, 1)
        self.assertEqual(position.version, 0)
        self.assertEqual(entry.quantity_delta.value, Decimal(4))
        with self.assertRaises(FrozenInstanceError):
            changed.on_hand_qty = QuantityVO(Decimal(0))


if __name__ == "__main__":
    unittest.main()
