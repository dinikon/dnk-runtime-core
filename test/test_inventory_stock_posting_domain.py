"""Неизменяемые проведения, баланс внутреннего перемещения и точная компенсация."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from src.modules.inventory.domain.error import (
    NegativeStockQuantityError,
    QuantityConversionMismatchError,
    QuantityStepError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_movement_balance import (
    StockMovementBalancePolicy,
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
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockPositionSnapshotError,
)
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
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
    DuplicateStockLedgerEntryError,
    InvalidPostingContextError,
    InvalidPostingSourceError,
    InvalidStockPostingSnapshotError,
    InvalidStockPostingValueError,
    InvalidStockReversalError,
    StockMovementBalanceError,
    StockPostingSignError,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
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
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockPostingDomainTests(unittest.TestCase):
    """Проверяет журнал по снимкам, сохраняя самостоятельность физических позиций."""

    def setUp(self) -> None:
        """Готовит весовой товар, две локации одного склада и исходный остаток."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("GRAIN"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.first_location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.warehouse.id, LocationType.STORAGE, True
        )
        self.second_location = replace(
            self.first_location, id=StockLocationIdVO(uuid4())
        )
        self.dimensions = StockDimensionsVO(
            self.item.id,
            self.first_location.id,
            StockOwnerIdVO(uuid4()),
            None,
            None,
            StockStatus.SELLABLE,
        )
        self.first = self.position(quantity="10")
        self.second = self.position(
            dimensions=replace(self.dimensions, location_id=self.second_location.id)
        )
        self.time = datetime(2026, 11, 3, 12, tzinfo=UTC)
        self.source = PostingSourceVO(StockExecutionIdVO(uuid4()))

    def position(self, quantity: str = "0", **changes: object) -> StockPosition:
        """Восстанавливает полный состав позиции, независимо от будущего хранения."""
        return StockPosition.restore(
            **(
                dict(
                    identifier=StockPositionIdVO(uuid4()),
                    dimensions=self.dimensions,
                    base_uom=self.item.base_uom,
                    on_hand_qty=QuantityVO(Decimal(quantity)),
                    version=0,
                )
                | changes
            )
        )

    def entry(
        self, delta: str = "5", position: StockPosition | None = None, **changes: object
    ) -> StockLedgerEntry:
        """Создаёт запись в базовой единице с явно сохранённым пересчётом 1:1."""
        target = self.first if position is None else position
        value = Decimal(delta)
        return StockLedgerEntry.create(
            **(
                dict(
                    identifier=StockLedgerEntryIdVO(uuid4()),
                    position_id=target.id,
                    quantity_delta=StockDeltaVO(value),
                    base_uom=target.base_uom,
                    conversion=QuantityConversionSnapshotVO.create(
                        quantity=QuantityVO(value.copy_abs()),
                        uom=target.base_uom,
                        base_uom=target.base_uom,
                    ),
                )
                | changes
            )
        )

    def posting(self, **changes: object) -> StockPosting:
        """Создаёт обычное поступление с явными снимками и временем."""
        return StockPosting.create(
            **(
                dict(
                    identifier=StockPostingIdVO(uuid4()),
                    source=self.source,
                    operation_type=StockOperationType.RECEIPT,
                    posted_at=self.time,
                    entries=(self.entry(),),
                    positions=(self.first.snapshot(),),
                )
                | changes
            )
        )

    def movement(self, **changes: object) -> StockPosting:
        """Создаёт внутреннее перемещение пяти килограммов между двумя адресами."""
        return self.posting(
            **(
                dict(
                    operation_type=StockOperationType.INTERNAL_MOVE,
                    entries=(self.entry("-5"), self.entry("5", self.second)),
                    positions=(self.first.snapshot(), self.second.snapshot()),
                    locations=(self.first_location, self.second_location),
                )
                | changes
            )
        )

    def reverse(self, reference: StockPosting, **changes: object) -> StockPosting:
        """Создаёт полную компенсацию с новым исполнением и идентификаторами записей."""
        return StockPosting.create_reversal(
            **(
                dict(
                    identifier=StockPostingIdVO(uuid4()),
                    source=PostingSourceVO(StockExecutionIdVO(uuid4())),
                    posted_at=self.time + timedelta(minutes=1),
                    original=reference.snapshot(),
                    entry_ids=tuple(
                        StockLedgerEntryIdVO(uuid4()) for entry in reference.entries
                    ),
                    positions=(self.first.snapshot(),),
                )
                | changes
            )
        )

    def restore(self, original: StockPosting, **changes: object) -> StockPosting:
        """Восстанавливает собственные поля без актуальных снимков позиций."""
        return StockPosting.restore(
            **(
                dict(
                    identifier=original.id,
                    source=original.source,
                    operation_type=original.operation_type,
                    posted_at=original.posted_at,
                    entries=original.entries,
                    reversal_of_id=original.reversal_of_id,
                )
                | changes
            )
        )

    def apply(
        self, position: StockPosition, entry: StockLedgerEntry, **changes: object
    ) -> StockPosition:
        """Применяет запись отдельно через существующие инварианты физического остатка."""
        location = (
            self.first_location
            if position.dimensions.location_id == self.first_location.id
            else self.second_location
        )
        return position.apply_delta(
            entry.quantity_delta,
            **(
                dict(
                    inventory_item=self.item.stock_snapshot(),
                    location=location,
                    warehouse=self.warehouse,
                )
                | changes
            ),
        )

    def test_receipt_and_issue_create_finished_facts_without_touching_position(
        self,
    ) -> None:
        """Сохраняет знаки и основание без статусов подготовки и автоматического изменения остатков."""
        receipt = self.posting()
        issue = self.posting(
            operation_type=StockOperationType.ISSUE, entries=(self.entry("-2"),)
        )
        self.assertIsNone(receipt.reversal_of_id)
        self.assertEqual(issue.entries[0].quantity_delta.value, Decimal(-2))
        self.assertEqual(receipt.source.execution_id, self.source.execution_id)
        self.assertEqual(self.first.on_hand_qty.value, Decimal(10))
        self.assertEqual(self.first.version, 0)
        self.assertEqual(
            {kind.value for kind in StockOperationType},
            {"RECEIPT", "ISSUE", "INTERNAL_MOVE"},
        )

    def test_empty_raw_and_duplicate_entries_are_rejected(self) -> None:
        """Отклоняет пустой или сырой состав, повтор ID записи и повтор позиции."""
        entry = self.entry()
        for entries in ((), [entry], (None,), (Decimal(5),)):
            with (
                self.subTest(entries=entries),
                self.assertRaises(InvalidStockPostingValueError),
            ):
                self.posting(entries=entries)
        for entries in (
            (entry, entry),
            (entry, self.entry("2")),
            (entry, self.entry("2", self.second, identifier=entry.id)),
        ):
            with (
                self.subTest(entries=entries),
                self.assertRaises(DuplicateStockLedgerEntryError),
            ):
                self.posting(entries=entries)

    def test_signs_cannot_cancel_each_other_in_receipt_or_issue(self) -> None:
        """Проверяет каждую запись операции, а не знак общей суммы."""
        for kind, entries in (
            (StockOperationType.RECEIPT, (self.entry("-1"),)),
            (StockOperationType.ISSUE, (self.entry("1"),)),
            (
                StockOperationType.RECEIPT,
                (self.entry("5"), self.entry("-1", self.second)),
            ),
            (
                StockOperationType.ISSUE,
                (self.entry("-5"), self.entry("1", self.second)),
            ),
        ):
            with self.subTest(kind=kind), self.assertRaises(StockPostingSignError):
                self.posting(operation_type=kind, entries=entries)

    def test_time_requires_timezone_and_is_normalized_to_utc(self) -> None:
        """Не вызывает часы и сохраняет один момент независимо от переданного смещения."""
        local_time = datetime(2026, 11, 3, 14, tzinfo=timezone(timedelta(hours=2)))
        posting = self.posting(posted_at=local_time)
        self.assertEqual(posting.posted_at, self.time)
        self.assertIs(posting.posted_at.tzinfo, UTC)
        self.assertEqual(
            self.restore(posting, posted_at=local_time).posted_at, self.time
        )
        for invalid in (
            None,
            self.time.date(),
            datetime(2026, 11, 3),
            "2026-11-03T12:00:00Z",
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidStockPostingValueError),
            ):
                self.posting(posted_at=invalid)
        with self.assertRaises(InvalidStockPostingValueError):
            self.posting(
                posted_at=datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))
            )

    def test_source_and_identifiers_require_their_own_types(self) -> None:
        """Не принимает UUID исполнения вместо VO и не смешивает идентификаторы разных сущностей."""
        for value in (None, uuid4(), "execution", StockPostingIdVO(uuid4())):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidPostingSourceError),
            ):
                PostingSourceVO(value)
        for identifier_type in (StockPostingIdVO, StockExecutionIdVO):
            with (
                self.subTest(identifier_type=identifier_type),
                self.assertRaises(EntityIdTypeError),
            ):
                identifier_type("id")
        for changes in (
            dict(identifier=uuid4()),
            dict(source=None),
            dict(operation_type="RECEIPT"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockPostingValueError),
            ):
                self.posting(**changes)

    def test_positions_must_match_entries_exactly(self) -> None:
        """Требует типизированные, уникальные снимки ровно участвующих позиций с той же единицей."""
        for positions in (
            (),
            [self.first.snapshot()],
            (self.first,),
            (None,),
            (self.second.snapshot(),),
            (self.first.snapshot(), self.second.snapshot()),
            (self.first.snapshot(), self.first.snapshot()),
            (replace(self.first.snapshot(), base_uom=UomCodeVO("G")),),
        ):
            with (
                self.subTest(positions=positions),
                self.assertRaises(InvalidPostingContextError),
            ):
                self.posting(positions=positions)
        malformed = replace(self.first.snapshot(), id=uuid4())
        with self.assertRaises(InvalidStockPositionSnapshotError):
            self.posting(positions=(malformed,))
        with self.assertRaises(InvalidPostingContextError):
            self.posting(locations=(self.first_location,))

    def test_duplicate_physical_dimensions_are_rejected_locally(self) -> None:
        """Не допускает два ID позиций с одной комбинацией измерений в переданном наборе."""
        duplicate = self.position()
        with self.assertRaises(InvalidPostingContextError):
            self.posting(
                entries=(self.entry(), self.entry("1", duplicate)),
                positions=(self.first.snapshot(), duplicate.snapshot()),
            )

    def test_move_balances_per_item_and_preserves_position_state(self) -> None:
        """Две записи перемещения не изменяют исходные позиции, а дельты применяются отдельно."""
        posting = self.movement()
        self.assertEqual(
            tuple(entry.quantity_delta.value for entry in posting.entries),
            (Decimal(-5), Decimal(5)),
        )
        source = self.apply(self.first, posting.entries[0])
        destination = self.apply(self.second, posting.entries[1])
        self.assertEqual(
            (source.on_hand_qty.value, destination.on_hand_qty.value),
            (Decimal(5), Decimal(5)),
        )
        self.assertEqual((source.version, destination.version), (1, 1))
        self.assertEqual(
            (self.first.on_hand_qty.value, self.second.on_hand_qty.value),
            (Decimal(10), Decimal(0)),
        )

    def test_move_cannot_change_any_preserved_dimension_even_when_global_sum_is_zero(
        self,
    ) -> None:
        """Общий нулевой итог не разрешает подменить товар, собственника, партию, серию или состояние."""
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lot_id=StockLotIdVO(uuid4())),
            dict(stock_status=StockStatus.BLOCKED),
        ):
            destination = self.position(
                dimensions=replace(self.second.dimensions, **changes)
            )
            with (
                self.subTest(changes=changes),
                self.assertRaises(StockMovementBalanceError),
            ):
                self.movement(
                    entries=(self.entry("-5"), self.entry("5", destination)),
                    positions=(self.first.snapshot(), destination.snapshot()),
                )

    def test_move_cannot_change_base_unit_or_quantity(self) -> None:
        """Не складывает килограммы с граммами и не допускает одностороннее движение или расхождение."""
        destination = self.position(
            dimensions=self.second.dimensions, base_uom=UomCodeVO("G")
        )
        with self.assertRaises(StockMovementBalanceError):
            self.movement(
                entries=(self.entry("-5"), self.entry("5", destination)),
                positions=(self.first.snapshot(), destination.snapshot()),
            )
        for entries, positions, locations in (
            (
                (self.entry("-5"), self.entry("4", self.second)),
                (self.first.snapshot(), self.second.snapshot()),
                (self.first_location, self.second_location),
            ),
            ((self.entry("5"),), (self.first.snapshot(),), (self.first_location,)),
            ((self.entry("-5"),), (self.first.snapshot(),), (self.first_location,)),
        ):
            with (
                self.subTest(entries=entries),
                self.assertRaises(StockMovementBalanceError),
            ):
                self.movement(entries=entries, positions=positions, locations=locations)

    def test_move_requires_distinct_locations_in_one_warehouse(self) -> None:
        """Не допускает межскладскую операцию под видом внутренней и недостаточный контекст адресов."""
        foreign = replace(self.second_location, warehouse_id=WarehouseIdVO(uuid4()))
        with self.assertRaises(StockMovementBalanceError):
            self.movement(locations=(self.first_location, foreign))
        for locations in (
            (),
            [self.first_location, self.second_location],
            (None,),
            (self.first_location,),
            (self.first_location, self.second_location, self.second_location),
        ):
            with (
                self.subTest(locations=locations),
                self.assertRaises(InvalidPostingContextError),
            ):
                self.movement(locations=locations)
        same_address = self.position(
            dimensions=replace(self.dimensions, owner_id=StockOwnerIdVO(uuid4()))
        )
        with self.assertRaises(StockMovementBalanceError):
            self.movement(
                entries=(self.entry("-5"), self.entry("5", same_address)),
                positions=(self.first.snapshot(), same_address.snapshot()),
                locations=(self.first_location,),
            )

    def test_multiple_items_cannot_cover_each_others_difference(self) -> None:
        """Разрешает несколько сбалансированных товаров, но не взаимное покрытие их расхождений."""
        other_a = self.position(
            dimensions=replace(
                self.dimensions, inventory_item_id=InventoryItemIdVO(uuid4())
            )
        )
        other_b = self.position(
            dimensions=replace(other_a.dimensions, location_id=self.second_location.id)
        )
        positions = (
            self.first.snapshot(),
            self.second.snapshot(),
            other_a.snapshot(),
            other_b.snapshot(),
        )
        good = (
            self.entry("-5"),
            self.entry("5", self.second),
            self.entry("-3", other_a),
            self.entry("3", other_b),
        )
        posting = self.movement(entries=good, positions=positions)
        self.assertEqual(len(posting.entries), 4)
        bad = (
            self.entry("-5"),
            self.entry("4", self.second),
            self.entry("-3", other_a),
            self.entry("4", other_b),
        )
        with self.assertRaises(StockMovementBalanceError):
            self.movement(entries=bad, positions=positions)

    def test_balance_is_independent_of_global_decimal_context(self) -> None:
        """Точный баланс нескольких адресов не зависит от порядка записей и внешней точности."""
        third_location = replace(self.first_location, id=StockLocationIdVO(uuid4()))
        third = self.position(
            dimensions=replace(self.dimensions, location_id=third_location.id)
        )
        entries = (
            self.entry("123456789.12345", self.second),
            self.entry("-123456789.12346"),
            self.entry("0.00001", third),
        )
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            for sequence in (entries, tuple(reversed(entries))):
                posting = self.movement(
                    entries=sequence,
                    positions=(
                        self.first.snapshot(),
                        self.second.snapshot(),
                        third.snapshot(),
                    ),
                    locations=(
                        self.first_location,
                        self.second_location,
                        third_location,
                    ),
                )
                self.assertEqual(posting.entries, sequence)
            self.assertFalse(any(context.flags.values()))

    def test_serial_delta_is_one_and_serial_cannot_have_multiple_incoming_entries(
        self,
    ) -> None:
        """Для конкретного экземпляра разрешает только ±1 и по одной записи каждого направления."""
        dimensions = replace(self.dimensions, serial_id=StockSerialIdVO(uuid4()))
        first = self.position(
            quantity="1", dimensions=dimensions, base_uom=UomCodeVO("PCS")
        )
        second = self.position(
            dimensions=replace(dimensions, location_id=self.second_location.id),
            base_uom=UomCodeVO("PCS"),
        )
        posting = self.movement(
            entries=(self.entry("-1", first), self.entry("1", second)),
            positions=(first.snapshot(), second.snapshot()),
        )
        self.assertEqual(len(posting.entries), 2)
        for delta in ("2", "0.5", "-2"):
            kind = (
                StockOperationType.ISSUE
                if delta.startswith("-")
                else StockOperationType.RECEIPT
            )
            with (
                self.subTest(delta=delta),
                self.assertRaises(InvalidPostingContextError),
            ):
                self.posting(
                    operation_type=kind,
                    entries=(self.entry(delta, first),),
                    positions=(first.snapshot(),),
                )
        with self.assertRaises(InvalidPostingContextError):
            self.posting(
                entries=(self.entry("1", first), self.entry("1", second)),
                positions=(first.snapshot(), second.snapshot()),
            )
        wrong_serial = self.position(
            dimensions=replace(second.dimensions, serial_id=StockSerialIdVO(uuid4())),
            base_uom=UomCodeVO("PCS"),
        )
        with self.assertRaises(StockMovementBalanceError):
            self.movement(
                entries=(self.entry("-1", first), self.entry("1", wrong_serial)),
                positions=(first.snapshot(), wrong_serial.snapshot()),
            )

    def test_reversal_creates_full_opposite_entries_with_new_identity_and_source(
        self,
    ) -> None:
        """Компенсация сохраняет позицию, единицу и исходный пересчёт, меняя знак и ID."""
        for kind, delta in (
            (StockOperationType.RECEIPT, "5"),
            (StockOperationType.ISSUE, "-5"),
        ):
            original = self.posting(operation_type=kind, entries=(self.entry(delta),))
            reversal = self.reverse(original)
            self.assertNotEqual(reversal.id, original.id)
            self.assertNotEqual(reversal.source, original.source)
            self.assertEqual(reversal.reversal_of_id, original.id)
            self.assertEqual(reversal.operation_type, original.operation_type)
            self.assertEqual(
                reversal.entries[0].quantity_delta.value, Decimal(delta).copy_negate()
            )
            self.assertNotEqual(reversal.entries[0].id, original.entries[0].id)
            self.assertEqual(
                reversal.entries[0].position_id, original.entries[0].position_id
            )
            self.assertIs(
                reversal.entries[0].conversion, original.entries[0].conversion
            )
            self.assertEqual(original.entries[0].quantity_delta.value, Decimal(delta))
            self.assertEqual(self.restore(reversal), reversal)

    def test_move_reversal_is_balanced_and_uses_all_original_positions(self) -> None:
        """Компенсация перемещения меняет знаки обеих сторон без новых измерений."""
        original = self.movement()
        reversal = self.reverse(
            original,
            positions=(self.first.snapshot(), self.second.snapshot()),
            locations=(self.first_location, self.second_location),
        )
        self.assertEqual(
            tuple(entry.quantity_delta.value for entry in reversal.entries),
            (Decimal(5), Decimal(-5)),
        )
        with self.assertRaises(InvalidPostingContextError):
            self.reverse(original)

    def test_reversal_cannot_reuse_identity_source_entries_or_go_back_in_time(
        self,
    ) -> None:
        """Отклоняет неполный состав, старые ID, прежнее исполнение и более раннюю компенсацию."""
        original = self.posting()
        for changes in (
            dict(identifier=original.id),
            dict(identifier=uuid4()),
            dict(source=original.source),
            dict(source=None),
            dict(posted_at=self.time - timedelta(seconds=1)),
            dict(entry_ids=()),
            dict(entry_ids=[]),
            dict(entry_ids=(uuid4(),)),
            dict(entry_ids=(original.entries[0].id,)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockReversalError),
            ):
                self.reverse(original, **changes)
        with self.assertRaises(InvalidStockPostingSnapshotError):
            self.reverse(original, original=original)

    def test_reversal_entry_ids_must_be_unique(self) -> None:
        """Не создаёт две компенсирующие записи с одним новым идентификатором."""
        original = self.movement()
        entry_id = StockLedgerEntryIdVO(uuid4())
        with self.assertRaises(DuplicateStockLedgerEntryError):
            self.reverse(
                original,
                entry_ids=(entry_id, entry_id),
                positions=(self.first.snapshot(), self.second.snapshot()),
                locations=(self.first_location, self.second_location),
            )

    def test_reversal_preserves_historical_factor_while_new_posting_rejects_it(
        self,
    ) -> None:
        """Старый коэффициент не подменяется новым при компенсации проведённой истории."""
        historical = QuantityConversionSnapshotVO(
            QuantityVO(Decimal(5000)), UomCodeVO("G"), Decimal("0.002")
        )
        entry = StockLedgerEntry.restore(
            identifier=StockLedgerEntryIdVO(uuid4()),
            position_id=self.first.id,
            quantity_delta=StockDeltaVO(Decimal(10)),
            base_uom=UomCodeVO("KG"),
            conversion=historical,
        )
        original = self.restore(self.posting(), entries=(entry,))
        reversal = self.reverse(original)
        self.assertIs(reversal.entries[0].conversion, historical)
        self.assertEqual(reversal.entries[0].quantity_delta.value, Decimal(-10))
        with self.assertRaises(QuantityConversionMismatchError):
            self.posting(entries=(entry,))

    def test_restore_preserves_full_state_without_current_snapshots(self) -> None:
        """Restore не требует справочников позиций, сохраняет ID и исторический состав."""
        original = self.movement()
        restored = self.restore(original)
        self.assertEqual(restored, original)
        self.assertIs(restored.id, original.id)
        self.assertIs(restored.entries, original.entries)
        for changes in (
            dict(reversal_of_id=original.id),
            dict(reversal_of_id=uuid4()),
            dict(source="source"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockPostingValueError),
            ):
                self.restore(original, **changes)

    def test_snapshots_and_roots_are_immutable_and_minimal(self) -> None:
        """Снимок позиции не раскрывает остаток, а snapshot проведения сохраняет его дочерние записи."""
        position = self.first.snapshot()
        self.assertEqual(
            set(position.__dataclass_fields__), {"id", "dimensions", "base_uom"}
        )
        posting = self.posting()
        snapshot = posting.snapshot()
        self.assertIsInstance(snapshot, StockPostingSnapshot)
        self.assertIs(snapshot.entries, posting.entries)
        for obj, field, value in (
            (posting, "posted_at", self.time),
            (snapshot, "entries", ()),
            (posting.entries[0], "position_id", self.second.id),
            (position, "base_uom", UomCodeVO("G")),
            (posting.source, "execution_id", StockExecutionIdVO(uuid4())),
        ):
            with self.subTest(obj=type(obj)), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)

    def test_malformed_snapshot_or_direct_aggregate_does_not_bypass_validation(
        self,
    ) -> None:
        """Потребитель повторно проверяет снимок и не доверяет сырым dataclass-конструкторам."""
        original = self.posting()
        for snapshot in (
            replace(original.snapshot(), entries=()),
            replace(original.snapshot(), source=None),
        ):
            with (
                self.subTest(snapshot=snapshot),
                self.assertRaises(InvalidStockPostingValueError),
            ):
                self.reverse(original, original=snapshot)
        with self.assertRaises(InvalidStockPostingValueError):
            replace(original, entries=()).snapshot()
        with self.assertRaises(InvalidStockPositionSnapshotError):
            replace(self.first.snapshot(), base_uom="KG").ensure_valid()

    def test_inactive_locations_are_physical_history_not_permission_to_execute(
        self,
    ) -> None:
        """Создание журнала не подменяет будущую политику разрешения операции в неактивных адресах."""
        posting = self.movement(
            locations=(
                replace(self.first_location, is_active=False),
                replace(self.second_location, is_active=False),
            )
        )
        self.assertEqual(len(posting.entries), 2)

    def test_position_still_controls_step_negative_quantity_and_serial_presence(
        self,
    ) -> None:
        """Факт журнала не заменяет проверку применимости его дельты к текущему физическому остатку."""
        issue = self.posting(
            operation_type=StockOperationType.ISSUE, entries=(self.entry("-11"),)
        )
        with self.assertRaises(NegativeStockQuantityError):
            self.apply(self.first, issue.entries[0])
        receipt = self.posting(entries=(self.entry("0.03"),))
        with self.assertRaises(QuantityStepError):
            self.apply(self.first, receipt.entries[0])
        serial_item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("SERIAL"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.SERIAL,
        )
        dimensions = replace(
            self.dimensions,
            inventory_item_id=serial_item.id,
            serial_id=StockSerialIdVO(uuid4()),
        )
        serial_position = self.position(
            quantity="1", dimensions=dimensions, base_uom=UomCodeVO("PCS")
        )
        receipt = self.posting(
            entries=(self.entry("1", serial_position),),
            positions=(serial_position.snapshot(),),
        )
        with self.assertRaises(InvalidSerialStockQuantityError):
            self.apply(
                serial_position,
                receipt.entries[0],
                inventory_item=serial_item.stock_snapshot(),
                serial=StockSerialSnapshot(dimensions.serial_id, serial_item.id, None),
            )
        self.assertEqual(
            (self.first.on_hand_qty.value, serial_position.on_hand_qty.value),
            (Decimal(10), Decimal(1)),
        )

    def test_compensation_requires_available_stock_when_its_delta_is_applied(
        self,
    ) -> None:
        """Создание компенсации не отменяет проверку количества перед будущим сохранением."""
        original = self.posting()
        compensation = self.reverse(original)
        empty = replace(self.first, on_hand_qty=QuantityVO(Decimal(0)))
        with self.assertRaises(NegativeStockQuantityError):
            self.apply(empty, compensation.entries[0])
        self.assertEqual(empty.on_hand_qty.value, Decimal(0))
        self.assertEqual(original.entries[0].quantity_delta.value, Decimal(5))

    def test_reversing_compensation_creates_another_link_without_modifying_history(
        self,
    ) -> None:
        """Компенсация компенсации остаётся новым фактом, а глобальную допустимость определит сценарий."""
        original = self.posting()
        compensation = self.reverse(original)
        repeated = self.reverse(
            compensation, posted_at=self.time + timedelta(minutes=2)
        )
        self.assertEqual(repeated.reversal_of_id, compensation.id)
        self.assertEqual(repeated.entries[0].quantity_delta.value, Decimal(5))

    def test_public_balance_policy_rejects_duplicate_entries(self) -> None:
        """Самостоятельный вызов Policy не принимает повтор позиции даже при нулевом общем балансе."""
        entry = self.entry("-5")
        with self.assertRaises(DuplicateStockLedgerEntryError):
            StockMovementBalancePolicy.ensure_balanced(
                entries=(entry, entry, self.entry("10", self.second)),
                positions=(self.first.snapshot(), self.second.snapshot()),
                locations=(self.first_location, self.second_location),
            )


if __name__ == "__main__":
    unittest.main()
