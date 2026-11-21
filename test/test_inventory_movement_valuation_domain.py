"""Проверяемое основание будущего переноса стоимости по одной полной паре INTERNAL_MOVE."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_stock_posting_domain as posting_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_movement_valuation import (
    StockMovementValuationPolicy,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockMovementEntryPairError,
    InvalidStockMovementValuationSnapshotError,
    StockMovementBalanceError,
    StockMovementValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.movement_entry_pair import (
    StockMovementEntryPairVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class MovementValuationDomainTests(unittest.TestCase):
    """Проверяет пару, полный физический контекст и независимость основания от текущих настроек и остатков."""

    def setUp(self) -> None:
        """Готовит обычное перемещение пяти KG между двумя адресами одного склада."""
        self.f = posting_fixture.StockPostingDomainTests()
        self.f.setUp()
        self.posting = self.f.movement()
        self.pair = StockMovementEntryPairVO(
            self.posting.entries[0].id, self.posting.entries[1].id
        )
        self.positions = (self.f.first.snapshot(), self.f.second.snapshot())
        self.locations = (self.f.first_location, self.f.second_location)

    def produce(
        self, posting: StockPosting | None = None, **changes: object
    ) -> StockMovementValuationSnapshot:
        """Выделяет пару публичным методом корня по полным снимкам позиций и локаций."""
        target = self.posting if posting is None else posting
        return target.movement_valuation_snapshot(
            **(
                dict(pair=self.pair, positions=self.positions, locations=self.locations)
                | changes
            )
        )

    def groups(
        self, **dimension_changes: object
    ) -> tuple[StockPosting, StockPosition, StockPosition]:
        """Восстанавливает две исторические независимые группы по пять KG для проверки явного сопоставления сторон."""
        dimensions = replace(
            self.f.dimensions,
            **(dimension_changes or dict(owner_id=StockOwnerIdVO(uuid4()))),
        )
        a = self.f.position(dimensions=dimensions)
        b = self.f.position(
            dimensions=replace(dimensions, location_id=self.f.second_location.id)
        )
        posting = self.f.restore(
            self.posting,
            entries=(
                *self.posting.entries,
                self.f.entry("-5", a),
                self.f.entry("5", b),
            ),
        )
        return posting, a, b

    def serial_context(
        self, quantity: str = "1"
    ) -> tuple[StockPosting, tuple[StockPosition, ...]]:
        """Готовит серийную пару одной PCS с сохранением LOT и SERIAL на обеих сторонах."""
        dimensions = replace(
            self.f.dimensions,
            lot_id=StockLotIdVO(uuid4()),
            serial_id=StockSerialIdVO(uuid4()),
        )
        source = self.f.position(dimensions=dimensions, base_uom=UomCodeVO("PCS"))
        target = self.f.position(
            dimensions=replace(dimensions, location_id=self.f.second_location.id),
            base_uom=UomCodeVO("PCS"),
        )
        entries = (self.f.entry("-" + quantity, source), self.f.entry(quantity, target))
        posting = StockPosting.restore(
            identifier=self.posting.id,
            source=self.posting.source,
            operation_type=StockOperationType.INTERNAL_MOVE,
            posted_at=self.f.time,
            entries=entries,
            reversal_of_id=None,
        )
        return posting, (source, target)

    def test_producer_derives_pair_positions_warehouse_quantity_and_time(self) -> None:
        """Основание выводится из конкретных записей и сохраняет исторический контекст без цены."""
        snapshot = self.produce()
        self.assertEqual(snapshot.posting_id, self.posting.id)
        self.assertEqual(snapshot.pair, self.pair)
        self.assertEqual(snapshot.source_position, self.positions[0])
        self.assertEqual(snapshot.target_position, self.positions[1])
        self.assertEqual(snapshot.warehouse_id, self.f.warehouse.id)
        self.assertEqual(snapshot.quantity, QuantityVO(Decimal(5)))
        self.assertEqual(snapshot.moved_at, self.posting.posted_at)
        snapshot.ensure_valid()

    def test_pair_vo_requires_distinct_nominal_ledger_identifiers(self) -> None:
        """Пара не принимает сырые UUID, идентификатор позиции, None или одну запись с обеих сторон."""
        for outgoing, incoming in (
            (uuid4(), self.pair.incoming_entry_id),
            (self.pair.outgoing_entry_id, uuid4()),
            (self.f.first.id, self.pair.incoming_entry_id),
            (None, self.pair.incoming_entry_id),
            (self.pair.outgoing_entry_id, self.pair.outgoing_entry_id),
        ):
            with (
                self.subTest(outgoing=outgoing, incoming=incoming),
                self.assertRaises(InvalidStockMovementEntryPairError),
            ):
                StockMovementEntryPairVO(outgoing, incoming)

    def test_pair_and_snapshot_are_immutable(self) -> None:
        """Выбранные ссылки и готовое основание не предоставляют прямого редактирования."""
        snapshot = self.produce()
        for target, name, value in (
            (self.pair, "outgoing_entry_id", self.pair.incoming_entry_id),
            (snapshot, "quantity", QuantityVO(Decimal(1))),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(target, name, value)

    def test_reversed_directions_or_unknown_entry_are_rejected(self) -> None:
        """Полностью сбалансированное проведение не разрешает перепутать направления или выбрать чужой ID."""
        for pair in (
            StockMovementEntryPairVO(
                self.pair.incoming_entry_id, self.pair.outgoing_entry_id
            ),
            StockMovementEntryPairVO(
                StockLedgerEntryIdVO(uuid4()), self.pair.incoming_entry_id
            ),
            StockMovementEntryPairVO(
                self.pair.outgoing_entry_id, StockLedgerEntryIdVO(uuid4())
            ),
        ):
            with (
                self.subTest(pair=pair),
                self.assertRaises(StockMovementValuationSourceError),
            ):
                self.produce(pair=pair)

    def test_two_negative_or_two_positive_entries_cannot_form_pair(self) -> None:
        """Явная пара сохраняет направления даже при наличии нескольких групп в одном корректном движении."""
        posting, a, b = self.groups()
        for pair in (
            StockMovementEntryPairVO(posting.entries[0].id, posting.entries[2].id),
            StockMovementEntryPairVO(posting.entries[1].id, posting.entries[3].id),
        ):
            with self.assertRaises(StockMovementValuationSourceError):
                self.produce(
                    posting,
                    pair=pair,
                    positions=(*self.positions, a.snapshot(), b.snapshot()),
                )

    def test_selected_group_is_not_totalled_with_other_independent_group(self) -> None:
        """Основание описывает одну выбранную пару, а не сумму всех движений документа."""
        posting, a, b = self.groups()
        snapshot = self.produce(
            posting,
            pair=StockMovementEntryPairVO(posting.entries[2].id, posting.entries[3].id),
            positions=(*self.positions, a.snapshot(), b.snapshot()),
        )
        self.assertEqual(snapshot.quantity.value, Decimal(5))
        self.assertEqual(snapshot.source_position.id, a.id)
        self.assertEqual(snapshot.target_position.id, b.id)

    def test_incompatible_pair_inside_balanced_multigroup_posting_is_rejected(
        self,
    ) -> None:
        """Одинаковых количеств недостаточно при другом товаре, владельце, LOT или состоянии выбранной стороны."""
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lot_id=StockLotIdVO(uuid4())),
            dict(stock_status=StockStatus.QUARANTINE),
        ):
            posting, a, b = self.groups(**changes)
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockMovementValuationSnapshotError),
            ):
                self.produce(
                    posting,
                    pair=StockMovementEntryPairVO(
                        posting.entries[0].id, posting.entries[3].id
                    ),
                    positions=(*self.positions, a.snapshot(), b.snapshot()),
                )

    def test_correct_pair_cannot_hide_unbalanced_restored_other_group(self) -> None:
        """Проверяется весь физический баланс, включая невыбранные записи восстановленной истории."""
        posting, a, b = self.groups()
        broken = self.f.restore(
            posting, entries=(*posting.entries[:3], self.f.entry("4", b))
        )
        with self.assertRaises(StockMovementBalanceError):
            self.produce(
                broken, positions=(*self.positions, a.snapshot(), b.snapshot())
            )

    def test_unequal_full_sides_of_split_or_merged_movement_are_rejected(self) -> None:
        """Первый срез не сопоставляет часть расхода с несколькими приходами или наоборот."""
        third_location = replace(self.f.first_location, id=StockLocationIdVO(uuid4()))
        third = self.f.position(
            dimensions=replace(self.f.dimensions, location_id=third_location.id)
        )
        for entries in (
            (
                self.f.entry("-7"),
                self.f.entry("3", self.f.second),
                self.f.entry("4", third),
            ),
            (
                self.f.entry("-3"),
                self.f.entry("7", self.f.second),
                self.f.entry("-4", third),
            ),
        ):
            posting = self.f.movement(
                entries=entries,
                positions=(*self.positions, third.snapshot()),
                locations=(*self.locations, third_location),
            )
            pair = StockMovementEntryPairVO(entries[0].id, entries[1].id)
            with self.assertRaises(StockMovementValuationSourceError):
                self.produce(
                    posting,
                    pair=pair,
                    positions=(*self.positions, third.snapshot()),
                    locations=(*self.locations, third_location),
                )

    def test_receipt_issue_adjustment_and_movement_reversal_are_rejected(self) -> None:
        """Нужен обычный INTERNAL_MOVE, а не другое проведение или его компенсация."""
        receipt = self.f.posting()
        issue = self.f.posting(
            operation_type=StockOperationType.ISSUE, entries=(self.f.entry("-5"),)
        )
        adjustment = self.f.restore(
            self.posting, operation_type=StockOperationType.ADJUSTMENT
        )
        reversal = self.f.reverse(
            self.posting, positions=self.positions, locations=self.locations
        )
        for posting in (receipt, issue, adjustment, reversal):
            with (
                self.subTest(operation=posting.operation_type),
                self.assertRaises(StockMovementValuationSourceError),
            ):
                self.produce(posting)

    def test_context_requires_all_and_only_positions_and_locations(self) -> None:
        """Проверка всего движения требует полный уникальный контекст, а не только удобные снимки."""
        for changes in (
            dict(positions=self.positions[:1]),
            dict(positions=(self.positions[0], self.positions[0])),
            dict(locations=self.locations[:1]),
            dict(locations=(*self.locations, self.locations[0])),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.produce(**changes)

    def test_context_rejects_different_warehouse_or_wrong_base_unit(self) -> None:
        """Односкладское движение не может менять склад или базовую единицу позиции."""
        with self.assertRaises(StockMovementBalanceError):
            self.produce(
                locations=(
                    self.locations[0],
                    replace(self.locations[1], warehouse_id=WarehouseIdVO(uuid4())),
                )
            )
        with self.assertRaises(InventoryError):
            self.produce(
                positions=(
                    self.positions[0],
                    replace(self.positions[1], base_uom=UomCodeVO("G")),
                )
            )

    def test_policy_requires_specialized_types_and_immutable_collections(self) -> None:
        """Межагрегатная Policy принимает снимки и номинальную пару без прямых Aggregate Roots."""
        for changes in (
            dict(posting=self.posting),
            dict(pair=None),
            dict(pair=(self.pair.outgoing_entry_id, self.pair.incoming_entry_id)),
            dict(positions=[*self.positions]),
            dict(locations=[*self.locations]),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(StockMovementValuationSourceError),
            ):
                StockMovementValuationPolicy.build_snapshot(
                    **(
                        dict(
                            posting=self.posting.snapshot(),
                            pair=self.pair,
                            positions=self.positions,
                            locations=self.locations,
                        )
                        | changes
                    )
                )

    def test_corrupted_pair_is_revalidated_by_producer_and_snapshot(self) -> None:
        """Обход конструктора VO не позволяет подставить сырые или одинаковые ссылки в основание."""
        pair = object.__new__(StockMovementEntryPairVO)
        object.__setattr__(pair, "outgoing_entry_id", self.pair.outgoing_entry_id)
        object.__setattr__(pair, "incoming_entry_id", self.pair.outgoing_entry_id)
        with self.assertRaises(InvalidStockMovementEntryPairError):
            self.produce(pair=pair)
        with self.assertRaises(InvalidStockMovementEntryPairError):
            replace(self.produce(), pair=pair).ensure_valid()

    def test_inactive_locations_do_not_invalidate_posted_history(self) -> None:
        """Изменение текущей активности адресов не переоценивает уже проведённое движение."""
        snapshot = self.produce(
            locations=tuple(
                replace(location, is_active=False) for location in self.locations
            )
        )
        self.assertEqual(snapshot, self.produce())

    def test_historical_conversion_is_not_replaced_by_current_catalog_factor(
        self,
    ) -> None:
        """Количество берётся из сохранённого Ledger, включая исторический коэффициент G → KG."""
        original = self.f.entry("-2")
        outgoing = replace(
            original,
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(1000)), UomCodeVO("G"), Decimal(".002")
            ),
        )
        incoming = self.f.entry("2", self.f.second)
        posting = self.f.restore(self.posting, entries=(outgoing, incoming))
        snapshot = self.produce(
            posting, pair=StockMovementEntryPairVO(outgoing.id, incoming.id)
        )
        self.assertEqual(snapshot.quantity.value, Decimal(2))

    def test_ready_snapshot_requires_nominal_fields(self) -> None:
        """Аннотации не заменяют проверки собственных ссылок, позиций, склада и количества снимка."""
        snapshot = self.produce()
        for name in (
            "posting_id",
            "pair",
            "source_position",
            "target_position",
            "warehouse_id",
            "quantity",
        ):
            with (
                self.subTest(name=name),
                self.assertRaises(InvalidStockMovementValuationSnapshotError),
            ):
                replace(snapshot, **{name: None}).ensure_valid()

    def test_ready_snapshot_requires_positive_finite_decimal_quantity(self) -> None:
        """Неконечное или неположительное количество отклоняется и после обхода конструктора VO."""
        snapshot = self.produce()
        for value in (
            Decimal(0),
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            "5",
        ):
            qty = object.__new__(QuantityVO)
            object.__setattr__(qty, "value", value)
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockMovementValuationSnapshotError),
            ):
                replace(snapshot, quantity=qty).ensure_valid()

    def test_ready_snapshot_requires_different_positions_and_locations(self) -> None:
        """Одинаковая позиция или одинаковый адрес не описывают перенос между двумя позициями."""
        snapshot = self.produce()
        for target in (
            replace(snapshot.target_position, id=snapshot.source_position.id),
            replace(
                snapshot.target_position,
                dimensions=replace(
                    snapshot.target_position.dimensions,
                    location_id=snapshot.source_position.dimensions.location_id,
                ),
            ),
        ):
            with self.assertRaises(InvalidStockMovementValuationSnapshotError):
                replace(snapshot, target_position=target).ensure_valid()

    def test_ready_snapshot_preserves_all_dimensions_and_unit(self) -> None:
        """Готовое основание не разрешает изменить товар, владельца, LOT, SERIAL, состояние или единицу назначения."""
        snapshot = self.produce()
        dimensions = snapshot.target_position.dimensions
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lot_id=StockLotIdVO(uuid4())),
            dict(serial_id=StockSerialIdVO(uuid4())),
            dict(stock_status=StockStatus.BLOCKED),
        ):
            target = replace(
                snapshot.target_position, dimensions=replace(dimensions, **changes)
            )
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(snapshot, target_position=target).ensure_valid()
        with self.assertRaises(InvalidStockMovementValuationSnapshotError):
            replace(
                snapshot,
                target_position=replace(
                    snapshot.target_position, base_uom=UomCodeVO("L")
                ),
            ).ensure_valid()

    def test_serial_and_lot_identity_survive_valid_pair(self) -> None:
        """Одна PCS одной серии и партии сохраняется на обеих сторонах без свежих сроков или справочников."""
        posting, positions = self.serial_context()
        snapshot = self.produce(
            posting,
            pair=StockMovementEntryPairVO(posting.entries[0].id, posting.entries[1].id),
            positions=tuple(position.snapshot() for position in positions),
        )
        self.assertEqual(snapshot.quantity.value, Decimal(1))
        self.assertEqual(
            snapshot.source_position.dimensions.serial_id,
            snapshot.target_position.dimensions.serial_id,
        )
        self.assertEqual(
            snapshot.source_position.dimensions.lot_id,
            snapshot.target_position.dimensions.lot_id,
        )
        self.assertEqual(snapshot.source_position.base_uom, UomCodeVO("PCS"))
        with self.assertRaises(InvalidStockMovementValuationSnapshotError):
            replace(snapshot, quantity=QuantityVO(Decimal(2))).ensure_valid()
        changed = replace(
            snapshot.target_position,
            dimensions=replace(
                snapshot.target_position.dimensions, serial_id=StockSerialIdVO(uuid4())
            ),
        )
        with self.assertRaises(InvalidStockMovementValuationSnapshotError):
            replace(snapshot, target_position=changed).ensure_valid()

    def test_serial_multiple_units_are_rejected_in_restored_posting(self) -> None:
        """Повторная проверка физического контекста не допускает две PCS одной серии в паре."""
        posting, positions = self.serial_context("2")
        with self.assertRaises(InventoryError):
            self.produce(
                posting,
                pair=StockMovementEntryPairVO(
                    posting.entries[0].id, posting.entries[1].id
                ),
                positions=tuple(position.snapshot() for position in positions),
            )

    def test_time_comes_from_posting_in_utc_and_not_from_current_clock(self) -> None:
        """Явное aware-время проведения нормализовано корнем, а готовый снимок сохраняет его без замены."""
        posting = self.f.movement(
            posted_at=self.f.time.astimezone(timezone(timedelta(hours=2)))
        )
        snapshot = self.produce(
            posting,
            pair=StockMovementEntryPairVO(posting.entries[0].id, posting.entries[1].id),
        )
        self.assertEqual(snapshot.moved_at, self.f.time)
        for at in (
            None,
            self.f.time.replace(tzinfo=None),
            self.f.time.astimezone(timezone(timedelta(hours=2))),
        ):
            with self.subTest(at=at), self.assertRaises(InventoryError):
                replace(snapshot, moved_at=at).ensure_valid()

    def test_snapshot_rechecks_own_state_without_source_or_current_settings(
        self,
    ) -> None:
        """Для проверки сохранённого основания достаточно его собственного состава."""
        snapshot = self.produce()
        restored = StockMovementValuationSnapshot(
            **{field.name: getattr(snapshot, field.name) for field in fields(snapshot)}
        )
        restored.ensure_valid()
        self.assertEqual(restored, snapshot)

    def test_no_physical_mutation_or_duplicate_history_is_created(self) -> None:
        """Выделение основания не применяет Ledger и не меняет остатки, версии или исходный журнал."""
        original = self.posting.snapshot()
        before = (self.f.first.on_hand_qty, self.f.second.on_hand_qty)
        self.produce()
        self.assertEqual(self.posting.snapshot(), original)
        self.assertEqual((self.f.first.on_hand_qty, self.f.second.on_hand_qty), before)
        self.assertEqual((self.f.first.version, self.f.second.version), (0, 0))

    def test_movement_is_not_exported_as_receipt_or_issue_valuation(self) -> None:
        """Новое основание не превращает стороны перемещения в закупочный приход или обычный расход."""
        with self.assertRaises(InventoryError):
            self.posting.receipt_valuation_snapshot(
                ledger_entry_id=self.pair.incoming_entry_id,
                position=self.positions[1],
                location=self.locations[1],
            )
        with self.assertRaises(InventoryError):
            self.posting.issue_valuation_snapshot(
                ledger_entry_id=self.pair.outgoing_entry_id,
                position=self.positions[0],
                location=self.locations[0],
            )

    def test_hostile_decimal_context_preserves_quantity_and_full_balance(self) -> None:
        """Историческое дробное количество и баланс не округляются внешней точностью Decimal или traps."""
        posting = self.f.movement(
            entries=(
                self.f.entry("-123.456789"),
                self.f.entry("123.456789", self.f.second),
            )
        )
        pair = StockMovementEntryPairVO(posting.entries[0].id, posting.entries[1].id)
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            snapshot = self.produce(posting, pair=pair)
            snapshot.ensure_valid()
        self.assertEqual(snapshot.quantity.value, Decimal("123.456789"))


if __name__ == "__main__":
    unittest.main()
