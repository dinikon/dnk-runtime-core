import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, MAX_EMAX, Rounded, localcontext
from itertools import permutations
from unittest.mock import patch
from uuid import UUID, uuid4

from test.inventory_tracking_fixtures import posting_tracking_context
from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    NegativeStockQuantityError,
    QuantityConversionMismatchError,
    StockQuantityArithmeticError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_execution_posting import (
    StockExecutionPostingPolicy,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionPostingSnapshotError,
    InvalidStockExecutionValueError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
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
    InvalidStockPositionSnapshotError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.error import (
    DuplicateStockLedgerEntryError,
    InvalidPostingContextError,
    InvalidStockPostingEntryBindingError,
    InvalidStockPostingValueError,
    OpposingStockPositionMovementsError,
    StockPostingExecutionTimeError,
)
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
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
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ExecutionPostingDomainTests(unittest.TestCase):
    """Проверяет переход от завершённых фактических строк к неизменяемому Ledger без I/O."""

    def setUp(self) -> None:
        """Готовит товар, три локации и позиции с явно различимым порядком UUID."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("GRAIN"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.owner = StockOwnerIdVO(uuid4())
        self.locations = tuple(
            StockLocationSnapshot(
                StockLocationIdVO(uuid4()),
                self.warehouse.id,
                LocationType.STORAGE,
                True,
            )
            for index in range(3)
        )
        self.a, self.b, self.c = tuple(
            self.position(index, identifier=StockPositionIdVO(UUID(int=number)))
            for index, number in enumerate((30, 10, 20))
        )
        self.bindings = tuple(
            StockPostingEntryBindingVO(
                position.id, StockLedgerEntryIdVO(UUID(int=100 + index))
            )
            for index, position in enumerate((self.a, self.b, self.c))
        )
        self.time = datetime(2026, 11, 4, 9, tzinfo=UTC)
        self.document_id = StockDocumentIdVO(uuid4())
        self.document_line_id = StockDocumentLineIdVO(uuid4())

    def position(self, location: int = 0, **changes: object) -> StockPosition:
        """Восстанавливает физическую позицию без выдуманного начального количества."""
        return StockPosition.restore(
            **(
                dict(
                    identifier=StockPositionIdVO(uuid4()),
                    dimensions=StockDimensionsVO(
                        self.item.id,
                        self.locations[location].id,
                        self.owner,
                        None,
                        None,
                        StockStatus.SELLABLE,
                    ),
                    base_uom=self.item.base_uom,
                    on_hand_qty=QuantityVO(Decimal(0)),
                    version=0,
                )
                | changes
            )
        )

    def line(
        self,
        quantity: str = "2",
        position: StockPosition | None = None,
        item: InventoryItem | None = None,
        **changes: object,
    ) -> StockExecutionLine:
        """Создаёт фактическую строку, сохраняющую исходные единицы и коэффициент."""
        target = self.a if position is None else position
        product = self.item if item is None else item
        return StockExecutionLine.create(
            **(
                dict(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=self.document_line_id,
                    inventory_item=product.execution_snapshot(),
                    quantity=QuantityVO(Decimal(quantity)),
                    uom=product.base_uom,
                    route=ReceiptExecutionRouteVO(target.dimensions),
                )
                | changes
            )
        )

    def execution(
        self,
        lines: tuple[StockExecutionLine, ...] | None = None,
        kind: StockOperationType = StockOperationType.RECEIPT,
        **changes: object,
    ) -> StockExecution:
        """Восстанавливает уже выбранные фактические маршруты как завершённый состав исполнения."""
        return StockExecution.restore(
            **(
                dict(
                    identifier=StockExecutionIdVO(uuid4()),
                    document_id=self.document_id,
                    document_version=2,
                    operation_type=kind,
                    warehouse_id=self.warehouse.id,
                    owner_id=self.owner,
                    executed_at=self.time,
                    lines=(self.line(),) if lines is None else lines,
                )
                | changes
            )
        )

    def posting(
        self, reference: StockExecution | None = None, **changes: object
    ) -> StockPosting:
        """Строит проведение по явным снимкам и соответствиям позиций и ID записей."""
        original = self.execution() if reference is None else reference
        return StockPosting.create_from_execution(
            **(
                dict(
                    identifier=StockPostingIdVO(uuid4()),
                    execution=original.posting_snapshot(),
                    posted_at=self.time + timedelta(minutes=1),
                    positions=(self.a.snapshot(),),
                    locations=(self.locations[0],),
                    entry_bindings=(self.bindings[0],),
                )
                | posting_tracking_context(
                    changes.get("positions", (self.a.snapshot(),))
                )
                | changes
            )
        )

    def move_line(
        self, source: StockPosition, destination: StockPosition, quantity: str = "2"
    ) -> StockExecutionLine:
        """Описывает одно количество между двумя адресами без удвоения плана."""
        return self.line(
            quantity,
            source,
            route=InternalMoveExecutionRouteVO(
                source.dimensions, destination.dimensions
            ),
        )

    def test_receipt_aggregates_mixed_units_and_derives_source_and_operation(
        self,
    ) -> None:
        """Две фактические строки 2000 G и 3 KG образуют одну запись +5 KG с коэффициентом 1."""
        first = self.line("2000", uom=UomCodeVO("G"))
        second = self.line("3", document_line_id=StockDocumentLineIdVO(uuid4()))
        execution = self.execution((first, second))
        posting = self.posting(execution)
        self.assertEqual(posting.source.execution_id, execution.id)
        self.assertEqual(posting.operation_type, StockOperationType.RECEIPT)
        self.assertIsNone(posting.reversal_of_id)
        self.assertEqual(len(posting.entries), 1)
        entry = posting.entries[0]
        self.assertEqual(entry.id, self.bindings[0].entry_id)
        self.assertEqual(entry.position_id, self.a.id)
        self.assertEqual(entry.quantity_delta.value, Decimal(5))
        self.assertEqual(entry.conversion.quantity.value, Decimal(5))
        self.assertEqual(entry.conversion.uom, UomCodeVO("KG"))
        self.assertEqual(entry.conversion.factor_to_base, Decimal(1))
        self.assertEqual(first.conversion.quantity.value, Decimal(2000))
        self.assertEqual(first.conversion.factor_to_base, Decimal("0.001"))
        self.assertEqual(second.conversion.quantity.value, Decimal(3))
        self.assertIs(execution.lines[0], first)

    def test_single_contributor_also_uses_canonical_base_conversion(self) -> None:
        """Новая фабрика применяет единое правило нормализации даже к одной строке."""
        execution = self.execution((self.line("2000", uom=UomCodeVO("G")),))
        posting = self.posting(execution)
        self.assertEqual(posting.entries[0].conversion.quantity.value, Decimal(2))
        self.assertEqual(posting.entries[0].conversion.uom, UomCodeVO("KG"))
        self.assertEqual(execution.lines[0].conversion.uom, UomCodeVO("G"))

    def test_issue_aggregates_magnitudes_and_applies_negative_sign(self) -> None:
        """Направление выводится из маршрута, а исходные количества остаются положительными."""
        route = IssueExecutionRouteVO(self.a.dimensions)
        execution = self.execution(
            (self.line("2", route=route), self.line("3", route=route)),
            kind=StockOperationType.ISSUE,
        )
        posting = self.posting(execution)
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(-5))
        self.assertEqual(posting.entries[0].conversion.quantity.value, Decimal(5))
        self.assertTrue(all(line.quantity.value > 0 for line in execution.lines))

    def test_internal_move_splits_destinations_and_sums_one_source(self) -> None:
        """Перемещения A→B на 4 и A→C на 6 дают A:-10, B:+4, C:+6."""
        execution = self.execution(
            (self.move_line(self.a, self.b, "4"), self.move_line(self.a, self.c, "6")),
            kind=StockOperationType.INTERNAL_MOVE,
        )
        posting = self.posting(
            execution,
            positions=(self.a.snapshot(), self.b.snapshot(), self.c.snapshot()),
            locations=self.locations,
            entry_bindings=self.bindings,
        )
        amounts = {
            entry.position_id: entry.quantity_delta.value for entry in posting.entries
        }
        self.assertEqual(
            amounts,
            {self.a.id: Decimal(-10), self.b.id: Decimal(4), self.c.id: Decimal(6)},
        )
        self.assertEqual(
            execution.snapshot_for_document().lines[0].quantity.value, Decimal(10)
        )
        self.assertEqual(
            tuple(entry.position_id for entry in posting.entries),
            (self.b.id, self.c.id, self.a.id),
        )

    def test_internal_move_can_merge_several_sources_into_one_destination(self) -> None:
        """Два источника формируют один приход без повторной записи позиции назначения."""
        execution = self.execution(
            (self.move_line(self.a, self.c, "2"), self.move_line(self.b, self.c, "3")),
            kind=StockOperationType.INTERNAL_MOVE,
        )
        posting = self.posting(
            execution,
            positions=(self.a.snapshot(), self.b.snapshot(), self.c.snapshot()),
            locations=self.locations,
            entry_bindings=self.bindings,
        )
        self.assertEqual(
            {
                entry.position_id: entry.quantity_delta.value
                for entry in posting.entries
            },
            {self.a.id: Decimal(-2), self.b.id: Decimal(-3), self.c.id: Decimal(5)},
        )

    def test_opposing_flows_are_rejected_instead_of_netting_even_when_net_is_zero(
        self,
    ) -> None:
        """Позиция-посредник и встречные маршруты не скрываются нулём или остаточной дельтой."""
        for lines, positions, locations, bindings in (
            (
                (self.move_line(self.a, self.b), self.move_line(self.b, self.c)),
                (self.a.snapshot(), self.b.snapshot(), self.c.snapshot()),
                self.locations,
                self.bindings,
            ),
            (
                (self.move_line(self.a, self.b), self.move_line(self.b, self.a)),
                (self.a.snapshot(), self.b.snapshot()),
                self.locations[:2],
                self.bindings[:2],
            ),
            (
                (
                    self.move_line(self.a, self.b, "5"),
                    self.move_line(self.b, self.a, "2"),
                ),
                (self.a.snapshot(), self.b.snapshot()),
                self.locations[:2],
                self.bindings[:2],
            ),
        ):
            execution = self.execution(lines, kind=StockOperationType.INTERNAL_MOVE)
            with (
                self.subTest(lines=lines),
                self.assertRaises(OpposingStockPositionMovementsError),
            ):
                self.posting(
                    execution,
                    positions=positions,
                    locations=locations,
                    entry_bindings=bindings,
                )

    def test_positions_match_full_dimensions_and_base_unit(self) -> None:
        """Совпадение товара и адреса не позволяет заменить владельца, партию, серию или состояние."""
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(location_id=self.locations[1].id),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lot_id=StockLotIdVO(uuid4())),
            dict(stock_status=StockStatus.QUARANTINE),
        ):
            position = replace(
                self.a.snapshot(), dimensions=replace(self.a.dimensions, **changes)
            )
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidPostingContextError),
            ):
                self.posting(positions=(position,))
        with self.assertRaises(InvalidPostingContextError):
            self.posting(
                positions=(replace(self.a.snapshot(), base_uom=UomCodeVO("G")),)
            )

    def test_missing_extra_duplicate_and_raw_positions_are_rejected(self) -> None:
        """Не подставляет позиции по умолчанию и не принимает два ID с одним физическим ключом."""
        for positions in (
            (),
            [self.a.snapshot()],
            (self.a,),
            (None,),
            (self.b.snapshot(),),
            (self.a.snapshot(), self.b.snapshot()),
            (self.a.snapshot(), self.a.snapshot()),
            (self.a.snapshot(), replace(self.a.snapshot(), id=self.b.id)),
            (self.a.snapshot(), replace(self.b.snapshot(), id=self.a.id)),
        ):
            with (
                self.subTest(positions=positions),
                self.assertRaises(InvalidPostingContextError),
            ):
                self.posting(positions=positions)
        with self.assertRaises(InvalidStockPositionSnapshotError):
            self.posting(positions=(replace(self.a.snapshot(), id=uuid4()),))

    def test_locations_must_match_routes_and_execution_warehouse_for_every_operation(
        self,
    ) -> None:
        """Проверка принадлежности складу применяется и к односторонним движениям."""
        for changes in (
            dict(locations=()),
            dict(locations=[]),
            dict(locations=(None,)),
            dict(locations=(self.locations[0], self.locations[0])),
            dict(locations=self.locations[:2]),
            dict(
                locations=(
                    replace(self.locations[0], warehouse_id=WarehouseIdVO(uuid4())),
                )
            ),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidPostingContextError),
            ):
                self.posting(**changes)
        with self.assertRaises(InvalidStockLocationSnapshotError):
            self.posting(locations=(replace(self.locations[0], is_active=1),))
        execution = self.execution(
            (self.move_line(self.a, self.b),), kind=StockOperationType.INTERNAL_MOVE
        )
        with self.assertRaises(InvalidPostingContextError):
            self.posting(
                execution,
                positions=(self.a.snapshot(), self.b.snapshot()),
                entry_bindings=self.bindings[:2],
                locations=(
                    self.locations[0],
                    replace(self.locations[1], warehouse_id=WarehouseIdVO(uuid4())),
                ),
            )

    def test_entry_bindings_are_explicit_exact_unique_and_immutable(self) -> None:
        """Состав ID не зависит от порядка обхода строк и не генерируется внутри Domain."""
        for bindings in ((), [], (None,), self.bindings[:2], (self.bindings[1],)):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(InvalidStockPostingEntryBindingError),
            ):
                self.posting(entry_bindings=bindings)
        for bindings in (
            (self.bindings[0], self.bindings[0]),
            (
                self.bindings[0],
                StockPostingEntryBindingVO(self.b.id, self.bindings[0].entry_id),
            ),
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(DuplicateStockLedgerEntryError),
            ):
                self.posting(entry_bindings=bindings)
        for position_id, entry_id in (
            (uuid4(), self.bindings[0].entry_id),
            (self.a.id, uuid4()),
            (None, None),
        ):
            with self.assertRaises(InvalidStockPostingEntryBindingError):
                StockPostingEntryBindingVO(position_id, entry_id)
        with self.assertRaises(FrozenInstanceError):
            self.bindings[0].entry_id = StockLedgerEntryIdVO(uuid4())

    def test_distinct_items_lots_statuses_and_locations_are_not_merged(self) -> None:
        """Агрегация выполняется по полному ключу позиции, а не только по товару или адресу."""
        lot_item = replace(
            self.item, id=InventoryItemIdVO(uuid4()), tracking_mode=TrackingMode.LOT
        )
        other_item = replace(self.item, id=InventoryItemIdVO(uuid4()))
        positions = (
            self.a,
            self.position(
                dimensions=replace(self.a.dimensions, inventory_item_id=other_item.id)
            ),
            self.position(
                dimensions=replace(
                    self.a.dimensions,
                    inventory_item_id=lot_item.id,
                    lot_id=StockLotIdVO(uuid4()),
                )
            ),
            self.position(
                dimensions=replace(
                    self.a.dimensions, stock_status=StockStatus.QUARANTINE
                )
            ),
            self.b,
        )
        lines = tuple(
            self.line(
                str(index + 1),
                position,
                item=(
                    other_item
                    if index == 1
                    else (lot_item if index == 2 else self.item)
                ),
                document_line_id=StockDocumentLineIdVO(uuid4()),
            )
            for index, position in enumerate(positions)
        )
        bindings = tuple(
            StockPostingEntryBindingVO(position.id, StockLedgerEntryIdVO(uuid4()))
            for position in positions
        )
        posting = self.posting(
            self.execution(lines),
            positions=tuple(position.snapshot() for position in positions),
            locations=self.locations[:2],
            entry_bindings=bindings,
        )
        self.assertEqual(
            {
                entry.position_id: entry.quantity_delta.value
                for entry in posting.entries
            },
            {
                position.id: Decimal(index + 1)
                for index, position in enumerate(positions)
            },
        )

    def test_permutations_produce_same_entries_order_quantities_and_identity(
        self,
    ) -> None:
        """Все перестановки входных строк и снимков сохраняют итоговый порядок по UUID позиции."""
        lines = (self.line("2"), self.line("3", self.b), self.line("4"))
        original = self.execution(lines)
        posting_id = StockPostingIdVO(uuid4())
        expected = self.posting(
            original,
            identifier=posting_id,
            positions=(self.a.snapshot(), self.b.snapshot()),
            locations=self.locations[:2],
            entry_bindings=self.bindings[:2],
        )
        for sequence in permutations(lines):
            execution = replace(original, lines=sequence)
            posting = self.posting(
                execution,
                identifier=posting_id,
                positions=(self.b.snapshot(), self.a.snapshot()),
                locations=tuple(reversed(self.locations[:2])),
                entry_bindings=tuple(reversed(self.bindings[:2])),
            )
            self.assertEqual(posting, expected)
        self.assertEqual(
            tuple(entry.position_id for entry in expected.entries),
            (self.b.id, self.a.id),
        )

    def test_posted_at_is_explicit_utc_and_not_before_execution(self) -> None:
        """Проверяет хронологию без вызова часов и разрешает равное время факта и проведения."""
        execution = self.execution()
        same = self.posting(execution, posted_at=self.time)
        local = self.posting(
            execution,
            posted_at=datetime(2026, 11, 4, 11, tzinfo=timezone(timedelta(hours=2))),
        )
        self.assertEqual(same.posted_at, self.time)
        self.assertIs(local.posted_at.tzinfo, UTC)
        self.assertEqual(local.posted_at, self.time)
        with self.assertRaises(StockPostingExecutionTimeError):
            self.posting(execution, posted_at=self.time - timedelta(seconds=1))
        for value in (None, self.time.date(), self.time.replace(tzinfo=None), "time"):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockPostingValueError),
            ):
                self.posting(execution, posted_at=value)

    def test_posting_snapshot_preserves_detail_and_has_separate_responsibility(
        self,
    ) -> None:
        """Снимок для документа группирует по плану, снимок для Ledger сохраняет фактические строки."""
        execution = self.execution(
            (self.line("2000", uom=UomCodeVO("G")), self.line("3"))
        )
        snapshot = execution.posting_snapshot()
        self.assertEqual(
            set(snapshot.__dataclass_fields__),
            {
                "id",
                "operation_type",
                "warehouse_id",
                "owner_id",
                "executed_at",
                "lines",
            },
        )
        self.assertEqual(len(snapshot.lines), 2)
        self.assertEqual(len(execution.snapshot_for_document().lines), 1)
        for original, projected in zip(execution.lines, snapshot.lines, strict=True):
            self.assertEqual(projected.id, original.id)
            self.assertIs(projected.conversion, original.conversion)
            self.assertIs(projected.route, original.route)
            self.assertEqual(projected.quantity, original.quantity)
        snapshot.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            snapshot.operation_type = StockOperationType.ISSUE
        with self.assertRaises(FrozenInstanceError):
            snapshot.lines[0].quantity = QuantityVO(Decimal(1))

    def test_getter_validates_original_and_factory_requires_specialized_snapshot(
        self,
    ) -> None:
        """Фабрика не принимает корень, документный итог или произвольный объект вместо маршрутов."""
        execution = self.execution()
        with self.assertRaises(InvalidStockExecutionValueError):
            replace(execution, document_version=True).posting_snapshot()
        for value in (None, execution, execution.snapshot_for_document()):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockExecutionPostingSnapshotError),
            ):
                self.posting(execution=value)

    def test_snapshot_consumer_rejects_raw_header_and_fact_line_values(self) -> None:
        """Прямой dataclass-конструктор не обходит проверки типов, времени и непустого состава."""
        execution = self.execution()
        snapshot = execution.posting_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(operation_type="RECEIPT"),
            dict(warehouse_id=uuid4()),
            dict(owner_id=uuid4()),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=()),
            dict(lines=[]),
            dict(lines=(None,)),
            dict(lines=execution.lines),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionPostingSnapshotError),
            ):
                self.posting(execution=replace(snapshot, **changes))
        row = snapshot.lines[0]
        for changes in (
            dict(id=uuid4()),
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(quantity=Decimal(2)),
            dict(quantity=QuantityVO(Decimal(0))),
            dict(conversion=None),
            dict(route=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionPostingSnapshotError),
            ):
                self.posting(
                    execution=replace(snapshot, lines=(replace(row, **changes),))
                )

    def test_snapshot_revalidates_conversion_route_item_owner_and_unique_line_ids(
        self,
    ) -> None:
        """Повреждённый пересчёт и подмена физических реквизитов не становятся записями Ledger."""
        snapshot = self.execution().posting_snapshot()
        row = snapshot.lines[0]
        for changed, error in (
            (
                replace(row, quantity=QuantityVO(Decimal(3))),
                QuantityConversionMismatchError,
            ),
            (replace(row, base_uom=UomCodeVO("L")), IncompatibleUomError),
            (
                replace(row, inventory_item_id=InventoryItemIdVO(uuid4())),
                InvalidStockExecutionPostingSnapshotError,
            ),
            (
                replace(row, route=IssueExecutionRouteVO(self.a.dimensions)),
                InvalidStockExecutionPostingSnapshotError,
            ),
            (
                replace(
                    row,
                    route=ReceiptExecutionRouteVO(
                        replace(self.a.dimensions, owner_id=StockOwnerIdVO(uuid4()))
                    ),
                ),
                InvalidStockExecutionPostingSnapshotError,
            ),
        ):
            with self.subTest(changed=changed), self.assertRaises(error):
                self.posting(execution=replace(snapshot, lines=(changed,)))
        with self.assertRaises(InvalidStockExecutionPostingSnapshotError):
            self.posting(execution=replace(snapshot, lines=(row, row)))

    def test_serial_rows_produce_one_piece_each_and_move_keeps_same_identity(
        self,
    ) -> None:
        """Две отдельные серии остаются отдельными позициями, перемещение даёт ±1 PCS."""
        item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("SERIAL"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.SERIAL,
        )
        first = self.position(
            dimensions=replace(
                self.a.dimensions,
                inventory_item_id=item.id,
                serial_id=StockSerialIdVO(uuid4()),
            ),
            base_uom=item.base_uom,
        )
        second = self.position(
            dimensions=replace(first.dimensions, serial_id=StockSerialIdVO(uuid4())),
            base_uom=item.base_uom,
        )
        bindings = tuple(
            StockPostingEntryBindingVO(position.id, StockLedgerEntryIdVO(uuid4()))
            for position in (first, second)
        )
        execution = self.execution(
            (self.line("1", first, item=item), self.line("1", second, item=item))
        )
        posting = self.posting(
            execution,
            positions=(first.snapshot(), second.snapshot()),
            entry_bindings=bindings,
        )
        self.assertEqual(
            tuple(entry.quantity_delta.value for entry in posting.entries),
            (Decimal(1), Decimal(1)),
        )
        destination = self.position(
            1,
            dimensions=replace(first.dimensions, location_id=self.locations[1].id),
            base_uom=item.base_uom,
        )
        route = InternalMoveExecutionRouteVO(first.dimensions, destination.dimensions)
        movement = self.execution(
            (self.line("1", first, item=item, route=route),),
            kind=StockOperationType.INTERNAL_MOVE,
        )
        posting = self.posting(
            movement,
            positions=(first.snapshot(), destination.snapshot()),
            locations=self.locations[:2],
            entry_bindings=(
                bindings[0],
                StockPostingEntryBindingVO(
                    destination.id, StockLedgerEntryIdVO(uuid4())
                ),
            ),
        )
        self.assertEqual(
            {
                entry.position_id: entry.quantity_delta.value
                for entry in posting.entries
            },
            {first.id: Decimal(-1), destination.id: Decimal(1)},
        )

    def test_serial_snapshot_cannot_repeat_an_instance_or_change_piece_quantity(
        self,
    ) -> None:
        """Потребитель проверяет серийность даже у вручную собранного снимка."""
        item = replace(
            self.item,
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.SERIAL,
        )
        position = self.position(
            dimensions=replace(self.a.dimensions, serial_id=StockSerialIdVO(uuid4())),
            base_uom=UomCodeVO("PCS"),
        )
        execution = self.execution((self.line("1", position, item=item),))
        snapshot = execution.posting_snapshot()
        row = snapshot.lines[0]
        for lines in (
            (row, replace(row, id=StockExecutionLineIdVO(uuid4()))),
            (
                replace(
                    row,
                    quantity=QuantityVO(Decimal(2)),
                    conversion=QuantityConversionSnapshotVO(
                        QuantityVO(Decimal(2)), UomCodeVO("PCS"), Decimal(1)
                    ),
                ),
            ),
        ):
            with self.assertRaises(InvalidStockExecutionPostingSnapshotError):
                self.posting(execution=replace(snapshot, lines=lines))

    def test_decimal_context_cannot_round_aggregation_or_change_global_flags(
        self,
    ) -> None:
        """Большие величины и малые дельты суммируются точно при внешней точности 2."""
        lines = (self.line("12345678901234567890.05"), self.line("0.05"))
        execution = self.execution(lines)
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            posting = self.posting(execution)
            self.assertEqual(
                posting.entries[0].quantity_delta.value,
                Decimal("12345678901234567890.10"),
            )
            self.assertFalse(any(context.flags.values()))

    def test_extreme_sum_fails_with_controlled_domain_error(self) -> None:
        """Переполнение не превращается в Infinity или округлённое количество записи."""
        amount = str(Decimal((0, (9,), MAX_EMAX)))
        execution = self.execution((self.line(amount), self.line(amount)))
        with self.assertRaises(StockQuantityArithmeticError):
            self.posting(execution)

    def test_historical_input_factor_is_preserved_without_reinterpreting_fact(
        self,
    ) -> None:
        """Новая запись хранит базовый итог, а исходный исторический коэффициент остаётся в исполнении."""
        line = self.line("5")
        historical = replace(
            line,
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(2500)), UomCodeVO("G"), Decimal("0.002")
            ),
        )
        execution = self.execution((historical,))
        posting = self.posting(execution)
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(5))
        self.assertEqual(posting.entries[0].conversion.factor_to_base, Decimal(1))
        self.assertEqual(execution.lines[0].conversion.factor_to_base, Decimal("0.002"))
        self.assertEqual(execution.lines[0].conversion.quantity.value, Decimal(2500))

    def test_building_posting_does_not_register_progress_or_apply_delta(self) -> None:
        """Фабрика строит только факт журнала, оставляя атомарное проведение внешнему сценарию."""
        execution = self.execution()
        with (
            patch(
                "src.modules.inventory.domain.stock_document.aggregate.StockDocument.register_execution",
                side_effect=RuntimeError("Не регистрировать"),
            ),
            patch(
                "src.modules.inventory.domain.stock_position.aggregate.StockPosition.apply_delta",
                side_effect=RuntimeError("Не менять остаток"),
            ),
        ):
            posting = self.posting(execution)
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(2))
        self.assertEqual(self.a.on_hand_qty.value, Decimal(0))
        self.assertEqual(self.a.version, 0)
        self.assertEqual(execution.lines[0].quantity.value, Decimal(2))

    def test_stock_availability_is_still_checked_by_position_when_delta_is_applied(
        self,
    ) -> None:
        """Снимок позиции без количества не является доказательством достаточного остатка для расхода."""
        execution = self.execution(
            (self.line(route=IssueExecutionRouteVO(self.a.dimensions)),),
            kind=StockOperationType.ISSUE,
        )
        posting = self.posting(execution)
        with self.assertRaises(NegativeStockQuantityError):
            self.a.apply_delta(
                posting.entries[0].quantity_delta,
                inventory_item=self.item.stock_snapshot(),
                warehouse=self.warehouse,
                location=self.locations[0],
            )

    def test_posting_preparation_preserves_historical_inactive_location_affiliation(
        self,
    ) -> None:
        """Построение журнала проверяет принадлежность адреса, а разрешение операции остаётся сценарию исполнения."""
        posting = self.posting(locations=(replace(self.locations[0], is_active=False),))
        self.assertEqual(posting.entries[0].position_id, self.a.id)

    def test_new_posting_restores_and_reverses_without_modifying_execution_detail(
        self,
    ) -> None:
        """Сформированный журнал совместим с существующими восстановлением и полной компенсацией."""
        execution = self.execution(
            (self.line("2000", uom=UomCodeVO("G")), self.line("3"))
        )
        posting = self.posting(execution)
        restored = StockPosting.restore(
            identifier=posting.id,
            source=posting.source,
            operation_type=posting.operation_type,
            posted_at=posting.posted_at,
            entries=posting.entries,
            reversal_of_id=None,
        )
        self.assertEqual(restored, posting)
        reversal = StockPosting.create_reversal(
            identifier=StockPostingIdVO(uuid4()),
            source=PostingSourceVO(StockExecutionIdVO(uuid4())),
            posted_at=self.time + timedelta(minutes=2),
            original=posting.snapshot(),
            entry_ids=(StockLedgerEntryIdVO(uuid4()),),
            positions=(self.a.snapshot(),),
        )
        self.assertEqual(reversal.entries[0].quantity_delta.value, Decimal(-5))
        self.assertEqual(execution.lines[0].conversion.quantity.value, Decimal(2000))
        with self.assertRaises(FrozenInstanceError):
            posting.entries = ()

    def test_policy_is_usable_directly_and_rejects_raw_execution(self) -> None:
        """Чистая Policy строит Entity журнала по явному контракту без вызова корня проведения."""
        execution = self.execution()
        values = dict(
            execution=execution.posting_snapshot(),
            positions=(self.a.snapshot(),),
            locations=(self.locations[0],),
            entry_bindings=(self.bindings[0],),
        )
        entries = StockExecutionPostingPolicy.build_entries(**values)
        self.assertEqual(entries, self.posting(execution).entries)
        with self.assertRaises(InvalidStockExecutionPostingSnapshotError):
            StockExecutionPostingPolicy.build_entries(
                **(values | dict(execution=execution))
            )


if __name__ == "__main__":
    unittest.main()
