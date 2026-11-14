"""Фактическое исполнение, маршруты, прослеживаемость и накопленный прогресс документа."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.error import (
    ExpirationDateNotAllowedError,
    ExpirationDateRequiredError,
    InvalidQuantityConversionError,
    QuantityConversionMismatchError,
    QuantityStepError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemExecutionSnapshotError,
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
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentExecutionSnapshotError,
    InvalidStockDocumentLineError,
    InvalidStockDocumentValueError,
    StaleStockDocumentVersionError,
    StockDocumentExecutionNotAllowedError,
    StockDocumentNotDraftError,
    StockDocumentOverExecutionError,
    StockDocumentTimeError,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    DuplicateStockExecutionLineError,
    DuplicateStockExecutionSerialError,
    InvalidStockExecutionContextError,
    InvalidStockExecutionDocumentSnapshotError,
    InvalidStockExecutionLineError,
    InvalidStockExecutionRouteError,
    InvalidStockExecutionValueError,
    StockExecutionTimeError,
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
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
    StockLocationInactiveError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockTrackingDimensionsError,
    StockDimensionsMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
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
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockExecutionDomainTests(unittest.TestCase):
    """Проверяет фактические строки и согласование прогресса по версии плана без хранения."""

    def setUp(self) -> None:
        """Готовит подтверждённый план приёмки 100 кг с двумя адресами одного склада."""
        self.prepare()

    def prepare(
        self,
        mode: TrackingMode = TrackingMode.NONE,
        kind: StockOperationType = StockOperationType.RECEIPT,
        expiration: ExpirationMode = ExpirationMode.NONE,
        plan: str = "100",
        dates: StockDatesVO | None = None,
    ) -> None:
        """Создаёт реальные карточки товара, склада, партии и экземпляра выбранного режима."""
        self.time = datetime(2026, 11, 3, 9, tzinfo=UTC)
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO("PCS" if mode.requires_serial else "KG"),
            quantity_rules=QuantityRulesVO(
                Decimal("1" if mode.requires_serial else "0.05")
            ),
            tracking_mode=mode,
            expiration_mode=expiration,
        )
        self.warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("MAIN"),
            name=WarehouseNameVO("Склад"),
        )
        self.a = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("A"),
            name=LocationNameVO("A"),
            location_type=LocationType.STORAGE,
        )
        self.b = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("B"),
            name=LocationNameVO("B"),
            location_type=LocationType.STORAGE,
        )
        self.owner = StockOwnerIdVO(uuid4())
        self.lot = (
            StockLot.restore(
                identifier=StockLotIdVO(uuid4()),
                inventory_item_id=self.item.id,
                number=LotNumberVO("LOT"),
                dates=StockDatesVO() if dates is None else dates,
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
        self.dimensions = StockDimensionsVO(
            self.item.id,
            self.a.id,
            self.owner,
            self.lot.id if self.lot else None,
            self.serial.id if self.serial else None,
            StockStatus.SELLABLE,
        )
        draft = StockDocument.create(
            identifier=StockDocumentIdVO(uuid4()),
            operation_type=kind,
            warehouse=self.warehouse.snapshot(),
            owner_id=self.owner,
            created_at=self.time,
        )
        self.planned_line = StockDocumentLine.create(
            identifier=StockDocumentLineIdVO(uuid4()),
            inventory_item=self.item.document_snapshot(),
            quantity=QuantityVO(Decimal(plan)),
            uom=self.item.base_uom,
        )
        self.draft = draft.add_line(
            self.planned_line,
            inventory_item=self.item.document_snapshot(),
            updated_at=self.at(1),
        )
        self.document = self.draft.confirm(
            warehouse=self.warehouse.snapshot(),
            inventory_items=(self.item.document_snapshot(),),
            updated_at=self.at(2),
        )

    def at(self, minute: int) -> datetime:
        """Возвращает явно заданное время сценария."""
        return self.time + timedelta(minutes=minute)

    def route(
        self,
    ) -> ReceiptExecutionRouteVO | IssueExecutionRouteVO | InternalMoveExecutionRouteVO:
        """Выбирает типизированный маршрут по операции документа."""
        if self.document.operation_type is StockOperationType.RECEIPT:
            return ReceiptExecutionRouteVO(self.dimensions)
        if self.document.operation_type is StockOperationType.ISSUE:
            return IssueExecutionRouteVO(self.dimensions)
        return InternalMoveExecutionRouteVO(
            self.dimensions, replace(self.dimensions, location_id=self.b.id)
        )

    def line(
        self, quantity: str | None = None, **changes: object
    ) -> StockExecutionLine:
        """Создаёт фактическую строку в базовой единице с возможностью сменить исходный ввод."""
        amount = "1" if self.item.tracking_mode.requires_serial else "10"
        return StockExecutionLine.create(
            **(
                dict(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=self.planned_line.id,
                    inventory_item=self.item.execution_snapshot(),
                    quantity=QuantityVO(
                        Decimal(amount if quantity is None else quantity)
                    ),
                    uom=self.item.base_uom,
                    route=self.route(),
                )
                | changes
            )
        )

    def create(
        self, reference: StockDocument | None = None, **changes: object
    ) -> StockExecution:
        """Создаёт исполнение по выбранной актуальной версии плана и точному физическому контексту."""
        document = self.document if reference is None else reference
        locations = (
            (self.a.snapshot(), self.b.snapshot())
            if self.document.operation_type is StockOperationType.INTERNAL_MOVE
            else (self.a.snapshot(),)
        )
        return StockExecution.create(
            **(
                dict(
                    identifier=StockExecutionIdVO(uuid4()),
                    document=document.execution_snapshot(),
                    executed_at=document.updated_at + timedelta(minutes=1),
                    lines=(self.line(),),
                    warehouse=self.warehouse.snapshot(),
                    inventory_items=(self.item.execution_snapshot(),),
                    locations=locations,
                    lots=(self.lot.snapshot(),) if self.lot else (),
                    serials=(self.serial.snapshot(),) if self.serial else (),
                )
                | changes
            )
        )

    def restore(self, original: StockExecution, **changes: object) -> StockExecution:
        """Восстанавливает полный собственный состав без текущего плана и справочников."""
        return StockExecution.restore(
            **(
                dict(
                    identifier=original.id,
                    document_id=original.document_id,
                    document_version=original.document_version,
                    operation_type=original.operation_type,
                    warehouse_id=original.warehouse_id,
                    owner_id=original.owner_id,
                    executed_at=original.executed_at,
                    lines=original.lines,
                )
                | changes
            )
        )

    def restore_document(
        self, original: StockDocument, **changes: object
    ) -> StockDocument:
        """Восстанавливает документ с выбранным прогрессом для проверки собственных инвариантов."""
        return StockDocument.restore(
            **(
                dict(
                    identifier=original.id,
                    operation_type=original.operation_type,
                    warehouse_id=original.warehouse_id,
                    owner_id=original.owner_id,
                    source=original.source,
                    status=original.status,
                    lines=original.lines,
                    created_at=original.created_at,
                    updated_at=original.updated_at,
                    version=original.version,
                )
                | changes
            )
        )

    def test_partial_execution_40_35_25_updates_each_version_and_remaining_quantity(
        self,
    ) -> None:
        """Достигает полного исполнения тремя независимыми фактами без изменения исходного плана."""
        document = self.document
        for amount, done, remaining, status, version in (
            ("40", "40", "60", StockDocumentStatus.PARTIALLY_EXECUTED, 3),
            ("35", "75", "25", StockDocumentStatus.PARTIALLY_EXECUTED, 4),
            ("25", "100", "0", StockDocumentStatus.COMPLETED, 5),
        ):
            execution = self.create(document, lines=(self.line(amount),))
            previous = document
            document = document.register_execution(
                execution.snapshot_for_document(),
                updated_at=execution.executed_at + timedelta(minutes=1),
            )
            self.assertEqual(document.status, status)
            self.assertEqual(document.version, version)
            self.assertEqual(document.lines[0].executed_qty.value, Decimal(done))
            self.assertEqual(document.lines[0].remaining_qty.value, Decimal(remaining))
            self.assertEqual(document.lines[0].planned_qty.value, Decimal(100))
            self.assertEqual(previous.version, version - 1)
        self.assertEqual(self.document.status, StockDocumentStatus.CONFIRMED)
        self.assertEqual(self.document.lines[0].executed_qty.value, Decimal(0))
        self.assertEqual(self.document.lines[0].remaining_qty.value, Decimal(100))

    def test_one_full_execution_completes_document_and_blocks_further_execution(
        self,
    ) -> None:
        """Полное количество переводит подтверждённый план сразу в COMPLETED."""
        execution = self.create(lines=(self.line("100"),))
        completed = self.document.register_execution(
            execution.snapshot_for_document(), updated_at=self.at(4)
        )
        self.assertEqual(completed.status, StockDocumentStatus.COMPLETED)
        with self.assertRaises(StockDocumentExecutionNotAllowedError):
            self.create(completed)
        with self.assertRaises(StockDocumentExecutionNotAllowedError):
            completed.register_execution(
                execution.snapshot_for_document(), updated_at=self.at(5)
            )

    def test_receipt_issue_and_move_preserve_positive_quantity_and_route(self) -> None:
        """Все операции исполняют положительный план; перемещение считается один раз."""
        for kind in (
            StockOperationType.RECEIPT,
            StockOperationType.ISSUE,
            StockOperationType.INTERNAL_MOVE,
        ):
            self.prepare(kind=kind)
            execution = self.create()
            snapshot = execution.snapshot_for_document()
            self.assertEqual(execution.operation_type, kind)
            self.assertEqual(snapshot.lines[0].quantity.value, Decimal(10))
            registered = self.document.register_execution(
                snapshot, updated_at=self.at(4)
            )
            self.assertEqual(registered.lines[0].executed_qty.value, Decimal(10))
            self.assertEqual(registered.lines[0].remaining_qty.value, Decimal(90))

    def test_multiple_actual_rows_are_summed_by_planned_line(self) -> None:
        """Одна плановая строка может исполняться несколькими отборами из разных локаций."""
        other = ReceiptExecutionRouteVO(replace(self.dimensions, location_id=self.b.id))
        execution = self.create(
            lines=(self.line("40"), self.line("35", route=other)),
            locations=(self.a.snapshot(), self.b.snapshot()),
        )
        summary = execution.snapshot_for_document()
        self.assertEqual(len(summary.lines), 1)
        self.assertEqual(summary.lines[0].quantity.value, Decimal(75))
        document = self.document.register_execution(summary, updated_at=self.at(4))
        self.assertEqual(document.lines[0].remaining_qty.value, Decimal(25))

    def test_overexecution_is_checked_after_grouping_and_against_remaining_plan(
        self,
    ) -> None:
        """Несколько допустимых по отдельности фактических строк не могут превысить план в сумме."""
        for lines in ((self.line("101"),), (self.line("40"), self.line("61"))):
            with (
                self.subTest(lines=lines),
                self.assertRaises(StockDocumentOverExecutionError),
            ):
                self.create(lines=lines)
        first = self.create(lines=(self.line("40"),))
        document = self.document.register_execution(
            first.snapshot_for_document(), updated_at=self.at(4)
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.create(document, lines=(self.line("61"),))

    def test_two_executions_prepared_from_same_version_cannot_both_register(
        self,
    ) -> None:
        """Версия предотвращает повторное использование старого лимита в последовательных Domain-вызовах."""
        first = self.create(lines=(self.line("40"),))
        second = self.create(lines=(self.line("70"),))
        document = self.document.register_execution(
            first.snapshot_for_document(), updated_at=self.at(4)
        )
        for snapshot in (second.snapshot_for_document(), first.snapshot_for_document()):
            with self.assertRaises(StaleStockDocumentVersionError):
                document.register_execution(snapshot, updated_at=self.at(5))
        with self.assertRaises(StockDocumentOverExecutionError):
            self.create(document, lines=second.lines)
        self.assertEqual(document.lines[0].executed_qty.value, Decimal(40))

    def test_each_planned_line_has_independent_limit_even_for_same_item(self) -> None:
        """Не покрывает превышение одной строки свободным количеством другой строки того же товара."""
        second_plan = StockDocumentLine.create(
            identifier=StockDocumentLineIdVO(uuid4()),
            inventory_item=self.item.document_snapshot(),
            quantity=QuantityVO(Decimal(100)),
            uom=self.item.base_uom,
        )
        draft = self.draft.add_line(
            second_plan,
            inventory_item=self.item.document_snapshot(),
            updated_at=self.at(2),
        )
        document = draft.confirm(
            warehouse=self.warehouse.snapshot(),
            inventory_items=(self.item.document_snapshot(),),
            updated_at=self.at(3),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.create(document, lines=(self.line("101"),))
        execution = self.create(
            document,
            lines=(self.line("100"), self.line("10", document_line_id=second_plan.id)),
        )
        document = document.register_execution(
            execution.snapshot_for_document(), updated_at=self.at(5)
        )
        self.assertEqual(
            tuple(line.executed_qty.value for line in document.lines),
            (Decimal(100), Decimal(10)),
        )
        self.assertEqual(document.status, StockDocumentStatus.PARTIALLY_EXECUTED)

    def test_foreign_planned_line_item_or_unit_cannot_be_used(self) -> None:
        """Фактическая строка должна соответствовать ID, товару и единице конкретной плановой строки."""
        with self.assertRaises(InvalidStockDocumentContextError):
            self.create(
                lines=(self.line(document_line_id=StockDocumentLineIdVO(uuid4())),)
            )
        execution = self.create()
        original = execution.snapshot_for_document()
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
            dict(document_line_id=StockDocumentLineIdVO(uuid4())),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDocumentContextError),
            ):
                self.document.register_execution(
                    replace(original, lines=(replace(original.lines[0], **changes),)),
                    updated_at=self.at(4),
                )

    def test_draft_and_cancelled_documents_cannot_execute(self) -> None:
        """Подготовка исполнения требует подтверждённого или частично исполненного плана."""
        for document in (
            self.draft,
            self.draft.cancel(updated_at=self.at(2)),
            self.document.cancel(updated_at=self.at(3)),
        ):
            with (
                self.subTest(status=document.status),
                self.assertRaises(StockDocumentExecutionNotAllowedError),
            ):
                self.create(document)

    def test_confirmed_without_progress_can_cancel_but_partial_and_complete_cannot(
        self,
    ) -> None:
        """Отмена подтверждённого плана доступна до первого исполнения без скрытого отката количества."""
        cancelled = self.document.cancel(updated_at=self.at(3))
        self.assertEqual(cancelled.status, StockDocumentStatus.CANCELLED)
        self.assertEqual(cancelled.version, self.document.version + 1)
        self.assertIs(cancelled.lines, self.document.lines)
        for amount in ("40", "100"):
            execution = self.create(lines=(self.line(amount),))
            document = self.document.register_execution(
                execution.snapshot_for_document(), updated_at=self.at(4)
            )
            with self.assertRaises(StockDocumentNotDraftError):
                document.cancel(updated_at=self.at(5))
            with self.assertRaises(StockDocumentNotDraftError):
                document.remove_line(self.planned_line.id, updated_at=self.at(5))

    def test_registration_verifies_document_operation_warehouse_and_owner(self) -> None:
        """Не регистрирует чужой или подменённый факт с теми же количествами."""
        snapshot = self.create().snapshot_for_document()
        for changes in (
            dict(document_id=StockDocumentIdVO(uuid4())),
            dict(operation_type=StockOperationType.ISSUE),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDocumentContextError),
            ):
                self.document.register_execution(
                    replace(snapshot, **changes), updated_at=self.at(4)
                )

    def test_time_is_explicit_utc_and_registration_cannot_precede_execution(
        self,
    ) -> None:
        """Нормализует часовой пояс и проверяет хронологию версии плана, факта и регистрации."""
        local = datetime(2026, 11, 3, 11, 3, tzinfo=timezone(timedelta(hours=2)))
        execution = self.create(executed_at=local)
        self.assertEqual(execution.executed_at, self.at(3))
        self.assertIs(execution.executed_at.tzinfo, UTC)
        for invalid in (
            None,
            self.time.date(),
            self.time.replace(tzinfo=None),
            "time",
            datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
            self.at(1),
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(StockExecutionTimeError),
            ):
                self.create(executed_at=invalid)
        with self.assertRaises(StockDocumentTimeError):
            self.document.register_execution(
                execution.snapshot_for_document(), updated_at=self.at(2)
            )
        registered = self.document.register_execution(
            execution.snapshot_for_document(), updated_at=self.at(3)
        )
        self.assertEqual(registered.updated_at, execution.executed_at)

    def test_route_shapes_are_strict_and_match_operation(self) -> None:
        """Не использует маршрут расхода для поступления и не принимает сырые физические ссылки."""
        with self.assertRaises(InvalidStockExecutionRouteError):
            self.create(
                lines=(self.line(route=IssueExecutionRouteVO(self.dimensions)),)
            )
        for factory in (ReceiptExecutionRouteVO, IssueExecutionRouteVO):
            with (
                self.subTest(factory=factory),
                self.assertRaises(InvalidStockExecutionRouteError),
            ):
                factory(None)
        with self.assertRaises(InvalidStockExecutionRouteError):
            InternalMoveExecutionRouteVO(self.dimensions, self.dimensions)
        with self.assertRaises(InvalidStockExecutionRouteError):
            InternalMoveExecutionRouteVO(None, self.dimensions)

    def test_move_cannot_change_any_dimension_except_location(self) -> None:
        """Перемещение сохраняет товар, владельца, партию, серию и состояние."""
        destination = replace(self.dimensions, location_id=self.b.id)
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lot_id=StockLotIdVO(uuid4())),
            dict(serial_id=StockSerialIdVO(uuid4())),
            dict(stock_status=StockStatus.BLOCKED),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionRouteError),
            ):
                InternalMoveExecutionRouteVO(
                    self.dimensions, replace(destination, **changes)
                )
        route = InternalMoveExecutionRouteVO(self.dimensions, destination)
        self.assertEqual(route.dimensions, (self.dimensions, destination))

    def test_move_requires_both_locations_in_same_active_warehouse(self) -> None:
        """Проверяет обе стороны фактического перемещения по снимкам склада и адресов."""
        self.prepare(kind=StockOperationType.INTERNAL_MOVE)
        for location, error in (
            (
                replace(self.b.snapshot(), warehouse_id=WarehouseIdVO(uuid4())),
                StockLocationWarehouseMismatchError,
            ),
            (replace(self.b.snapshot(), is_active=False), StockLocationInactiveError),
        ):
            with self.subTest(location=location), self.assertRaises(error):
                self.create(locations=(self.a.snapshot(), location))

    def test_inactive_foreign_and_malformed_warehouse_or_location_are_rejected(
        self,
    ) -> None:
        """Исполнение не разрешается административно неактивному адресу в отличие от физической истории."""
        for changes, error in (
            (
                dict(warehouse=self.warehouse.deactivate().snapshot()),
                WarehouseInactiveError,
            ),
            (
                dict(
                    warehouse=replace(
                        self.warehouse.snapshot(), id=WarehouseIdVO(uuid4())
                    )
                ),
                InvalidStockExecutionContextError,
            ),
            (dict(warehouse=self.warehouse), InvalidWarehouseSnapshotError),
            (
                dict(locations=(replace(self.a.snapshot(), is_active=False),)),
                StockLocationInactiveError,
            ),
            (
                dict(locations=(replace(self.a.snapshot(), id=uuid4()),)),
                InvalidStockLocationSnapshotError,
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                self.create(**changes)

    def test_exact_unique_item_and_location_snapshots_are_required(self) -> None:
        """Запрещает лишние, отсутствующие и повторные снимки, не подставляя контекст автоматически."""
        for changes in (
            dict(inventory_items=()),
            dict(inventory_items=[]),
            dict(
                inventory_items=(
                    self.item.execution_snapshot(),
                    self.item.execution_snapshot(),
                )
            ),
            dict(locations=()),
            dict(locations=[]),
            dict(locations=(self.a.snapshot(), self.a.snapshot())),
            dict(locations=(self.a.snapshot(), self.b.snapshot())),
            dict(lots=[]),
            dict(serials=[]),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionContextError),
            ):
                self.create(**changes)
        with self.assertRaises(InvalidInventoryItemExecutionSnapshotError):
            self.create(inventory_items=(self.item,))

    def test_owner_and_item_of_actual_dimensions_must_match(self) -> None:
        """Источник и назначение не позволяют подменить владельца документа или товар строки."""
        with self.assertRaises(InvalidStockExecutionContextError):
            self.create(
                lines=(
                    self.line(
                        route=ReceiptExecutionRouteVO(
                            replace(self.dimensions, owner_id=StockOwnerIdVO(uuid4()))
                        )
                    ),
                )
            )
        with self.assertRaises(InvalidStockExecutionLineError):
            self.line(
                route=ReceiptExecutionRouteVO(
                    replace(
                        self.dimensions, inventory_item_id=InventoryItemIdVO(uuid4())
                    )
                )
            )

    def test_actual_quantity_uses_system_conversion_and_current_step(self) -> None:
        """Сохраняет 1250 G как 1.25 KG и отклоняет некратный шагу фактический ввод."""
        line = self.line("1250", uom=UomCodeVO("G"))
        execution = self.create(lines=(line,))
        self.assertEqual(execution.lines[0].quantity.value, Decimal("1.25"))
        self.assertEqual(line.conversion.factor_to_base, Decimal("0.001"))
        with self.assertRaises(QuantityStepError):
            self.line("1230", uom=UomCodeVO("G"))
        with self.assertRaises(InvalidQuantityConversionError):
            self.line("0")
        current = replace(
            self.item.execution_snapshot(), quantity_rules=QuantityRulesVO(Decimal(3))
        )
        with self.assertRaises(QuantityStepError):
            self.create(inventory_items=(current,))
        with self.assertRaises(InvalidStockExecutionContextError):
            self.create(
                inventory_items=(
                    replace(self.item.execution_snapshot(), base_uom=UomCodeVO("G")),
                )
            )

    def test_tracking_matrix_requires_exact_physical_lot_and_serial(self) -> None:
        """Фактическое исполнение требует прослеживаемость, которую не требовал плановый документ."""
        for mode in TrackingMode:
            self.prepare(mode=mode)
            execution = self.create()
            self.assertEqual(
                execution.lines[0].route.dimensions[0].lot_id, self.dimensions.lot_id
            )
            if mode in (TrackingMode.LOT, TrackingMode.LOT_AND_SERIAL):
                with self.assertRaises(InvalidStockLotSnapshotError):
                    self.create(lots=())
            if mode.requires_serial:
                with self.assertRaises(InvalidStockSerialSnapshotError):
                    self.create(serials=())
            altered = (
                replace(self.dimensions, lot_id=None, serial_id=None)
                if mode is not TrackingMode.NONE
                else replace(self.dimensions, lot_id=StockLotIdVO(uuid4()))
            )
            with (
                self.subTest(mode=mode),
                self.assertRaises(InvalidStockTrackingDimensionsError),
            ):
                self.create(
                    lines=(self.line(route=ReceiptExecutionRouteVO(altered)),),
                    lots=(),
                    serials=(),
                )

    def test_required_receipt_date_comes_from_lot_or_standalone_serial(self) -> None:
        """Требует срок партии или собственный срок серии перед приёмкой REQUIRED."""
        for mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            self.prepare(mode=mode, expiration=ExpirationMode.REQUIRED)
            with (
                self.subTest(mode=mode),
                self.assertRaises(ExpirationDateRequiredError),
            ):
                self.create()
            self.prepare(
                mode=mode,
                expiration=ExpirationMode.REQUIRED,
                dates=StockDatesVO(expires_on=date(2027, 1, 1)),
            )
            self.assertIsInstance(self.create(), StockExecution)

    def test_optional_dates_are_notes_and_no_expiry_rejection_is_invented(self) -> None:
        """OPTIONAL не фильтрует даты; REQUIRED проверяет полноту без неутверждённого правила просрочки."""
        for expiration in (ExpirationMode.OPTIONAL, ExpirationMode.REQUIRED):
            self.prepare(
                mode=TrackingMode.LOT,
                expiration=expiration,
                dates=StockDatesVO(expires_on=date(2020, 1, 1)),
            )
            self.assertIsInstance(self.create(), StockExecution)
        self.prepare(
            mode=TrackingMode.LOT,
            expiration=ExpirationMode.NONE,
            dates=StockDatesVO(expires_on=date(2020, 1, 1)),
        )
        with self.assertRaises(ExpirationDateNotAllowedError):
            self.create()

    def test_lot_and_serial_snapshots_cannot_be_foreign_duplicate_or_surplus(
        self,
    ) -> None:
        """Проверяет принадлежность физических карточек товару и ровно участвующий набор ссылок."""
        self.prepare(mode=TrackingMode.LOT_AND_SERIAL)
        for changes, error in (
            (
                dict(
                    lots=(
                        replace(
                            self.lot.snapshot(),
                            inventory_item_id=InventoryItemIdVO(uuid4()),
                        ),
                    )
                ),
                StockDimensionsMismatchError,
            ),
            (
                dict(
                    serials=(
                        replace(
                            self.serial.snapshot(),
                            lot_id=StockLotIdVO(uuid4()),
                        ),
                    )
                ),
                StockDimensionsMismatchError,
            ),
            (
                dict(lots=(self.lot.snapshot(), self.lot.snapshot())),
                InvalidStockExecutionContextError,
            ),
            (
                dict(
                    serials=(
                        self.serial.snapshot(),
                        self.serial.snapshot(),
                    )
                ),
                InvalidStockExecutionContextError,
            ),
            (dict(serials=(self.serial,)), InvalidStockSerialSnapshotError),
            (dict(lots=(None,)), InvalidStockLotSnapshotError),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                self.create(**changes)
        unused = replace(self.lot.snapshot(), id=StockLotIdVO(uuid4()))
        with self.assertRaises(InvalidStockExecutionContextError):
            self.create(lots=(self.lot.snapshot(), unused))

    def test_serial_requires_one_piece_and_cannot_repeat_across_actual_rows(
        self,
    ) -> None:
        """Один маршрут перемещения использует один экземпляр с обеих сторон, повтор другой строкой запрещён."""
        for kind in (
            StockOperationType.RECEIPT,
            StockOperationType.ISSUE,
            StockOperationType.INTERNAL_MOVE,
        ):
            self.prepare(mode=TrackingMode.SERIAL, kind=kind)
            self.assertIsInstance(self.create(), StockExecution)
            for amount in ("2", "0.5"):
                with (
                    self.subTest(kind=kind, amount=amount),
                    self.assertRaises(InvalidStockExecutionLineError),
                ):
                    self.line(amount)
            with self.assertRaises(DuplicateStockExecutionSerialError):
                self.create(lines=(self.line(), self.line()))

    def test_twelve_serials_need_twelve_distinct_actual_rows(self) -> None:
        """Полный серийный план исполняется отдельной идентичностью каждого экземпляра."""
        self.prepare(mode=TrackingMode.SERIAL, plan="12")
        serials, lines = [], []
        for index in range(12):
            serial = StockSerial.restore(
                identifier=StockSerialIdVO(uuid4()),
                inventory_item_id=self.item.id,
                number=SerialNumberVO(str(index)),
                lot_id=None,
            )
            serials.append(serial.snapshot())
            lines.append(
                self.line(
                    route=ReceiptExecutionRouteVO(
                        replace(self.dimensions, serial_id=serial.id)
                    )
                )
            )
        execution = self.create(lines=tuple(lines), serials=tuple(serials))
        self.assertEqual(
            execution.snapshot_for_document().lines[0].quantity.value, Decimal(12)
        )
        document = self.document.register_execution(
            execution.snapshot_for_document(), updated_at=self.at(4)
        )
        self.assertEqual(document.status, StockDocumentStatus.COMPLETED)

    def test_execution_and_serial_snapshots_are_typed_and_keep_one_source_of_dates(
        self,
    ) -> None:
        """Новые контракты не расширяют старые минимальные снимки и повторно проверяют типы."""
        item = self.item.execution_snapshot()
        self.assertEqual(
            set(item.__dataclass_fields__),
            {
                "inventory_item_id",
                "base_uom",
                "quantity_rules",
                "tracking_mode",
                "expiration_mode",
            },
        )
        for changes in (
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(quantity_rules=None),
            dict(tracking_mode="LOT"),
            dict(expiration_mode="NONE"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidInventoryItemExecutionSnapshotError),
            ):
                replace(item, **changes).ensure_valid()
        with self.assertRaises(InvalidTrackingConfigurationError):
            replace(item, expiration_mode=ExpirationMode.REQUIRED).ensure_valid()
        self.prepare(mode=TrackingMode.SERIAL)
        snapshot = self.serial.snapshot()
        self.assertFalse(hasattr(snapshot, "dates"))
        self.assertEqual(
            set(self.serial.snapshot().__dataclass_fields__),
            {"id", "inventory_item_id", "lot_id"},
        )
        with self.assertRaises(InvalidStockSerialSnapshotError):
            replace(snapshot, inventory_item_id=uuid4()).ensure_valid()
        self.prepare(mode=TrackingMode.LOT_AND_SERIAL)
        with self.assertRaises(InvalidStockSerialSnapshotError):
            replace(self.serial.snapshot(), lot_id="LOT").ensure_valid()

    def test_line_ids_and_summary_ids_are_unique_and_typed(self) -> None:
        """Разрешает повтор плановой строки, но запрещает повтор фактического ID и повтор итоговой строки."""
        line = self.line()
        with self.assertRaises(DuplicateStockExecutionLineError):
            self.create(lines=(line, line))
        for identifier_type in (StockExecutionIdVO, StockExecutionLineIdVO):
            with (
                self.subTest(identifier_type=identifier_type),
                self.assertRaises(EntityIdTypeError),
            ):
                identifier_type("raw")
        snapshot = self.create().snapshot_for_document()
        with self.assertRaises(InvalidStockExecutionDocumentSnapshotError):
            replace(
                snapshot, lines=(snapshot.lines[0], snapshot.lines[0])
            ).ensure_valid()
        for changes in (
            dict(document_line_id=uuid4()),
            dict(quantity=QuantityVO(Decimal(0))),
            dict(base_uom="KG"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionDocumentSnapshotError),
            ):
                replace(snapshot.lines[0], **changes)

    def test_restore_preserves_full_own_state_without_current_snapshots(self) -> None:
        """Восстановление не требует справочников или повторного разрешения фактических дат и адресов."""
        original = self.create()
        with patch(
            "src.modules.inventory.domain.stock_execution.aggregate.StockExecutionContextPolicy.ensure_compatible",
            side_effect=RuntimeError("Не загружать контекст"),
        ):
            restored = self.restore(original)
        self.assertEqual(restored, original)
        self.assertIs(restored.id, original.id)
        self.assertIs(restored.lines, original.lines)
        self.assertEqual(restored.document_version, self.document.version)
        self.assertEqual(
            restored.snapshot_for_document(), original.snapshot_for_document()
        )

    def test_restore_checks_raw_fields_empty_lines_and_bad_versions(self) -> None:
        """Не восстанавливает сырые ссылки, bool-версию или пустой фактический состав."""
        execution = self.create()
        for changes in (
            dict(identifier=uuid4()),
            dict(document_id=uuid4()),
            dict(document_version=True),
            dict(document_version=-1),
            dict(operation_type="RECEIPT"),
            dict(owner_id=uuid4()),
            dict(warehouse_id=uuid4()),
            dict(lines=()),
            dict(lines=[]),
            dict(lines=(None,)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionValueError),
            ):
                self.restore(execution, **changes)
        with self.assertRaises(InvalidStockExecutionValueError):
            replace(execution, lines=()).snapshot_for_document()

    def test_line_restore_preserves_historical_factor_but_create_rejects_it(
        self,
    ) -> None:
        """Сохранённые исходные данные восстанавливаются, но новое исполнение требует актуального коэффициента."""
        original = self.line()
        conversion = QuantityConversionSnapshotVO(
            QuantityVO(Decimal(5000)), UomCodeVO("G"), Decimal("0.002")
        )
        line = StockExecutionLine.restore(
            identifier=original.id,
            document_line_id=original.document_line_id,
            inventory_item_id=original.inventory_item_id,
            base_uom=original.base_uom,
            quantity=original.quantity,
            conversion=conversion,
            route=original.route,
        )
        restored = self.restore(self.create(), lines=(line,))
        self.assertIs(restored.lines[0].conversion, conversion)
        with self.assertRaises(QuantityConversionMismatchError):
            self.create(lines=(line,))
        with self.assertRaises(InvalidStockExecutionLineError):
            replace(line, quantity=QuantityVO(Decimal(0))).ensure_valid()
        with self.assertRaises(QuantityConversionMismatchError):
            replace(line, quantity=QuantityVO(Decimal(11))).ensure_valid()

    def test_document_and_execution_snapshots_reject_malformed_fields(self) -> None:
        """Потребители не доверяют сырым dataclass-снимкам и проверяют их собственный состав."""
        document = self.document.execution_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(version=True),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=(None,)),
            dict(lines=(document.lines[0], document.lines[0])),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDocumentExecutionSnapshotError),
            ):
                self.create(document=replace(document, **changes))
        with self.assertRaises(InvalidStockDocumentExecutionSnapshotError):
            replace(
                document.lines[0], executed_qty=QuantityVO(Decimal(101))
            ).ensure_valid()
        execution = self.create().snapshot_for_document()
        for changes in (
            dict(id=uuid4()),
            dict(document_version=True),
            dict(lines=()),
            dict(lines=(None,)),
            dict(executed_at=self.time.replace(tzinfo=None)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockExecutionDocumentSnapshotError),
            ):
                self.document.register_execution(
                    replace(execution, **changes), updated_at=self.at(4)
                )
        with self.assertRaises(InvalidStockExecutionDocumentSnapshotError):
            self.document.register_execution(self.create(), updated_at=self.at(4))

    def test_document_status_and_progress_are_consistent_on_restore(self) -> None:
        """Собственное состояние не допускает исполненный черновик или ложное завершение плана."""
        partial = replace(self.planned_line, executed_qty=QuantityVO(Decimal(40)))
        full = replace(self.planned_line, executed_qty=QuantityVO(Decimal(100)))
        for status, lines in (
            (StockDocumentStatus.DRAFT, (partial,)),
            (StockDocumentStatus.CONFIRMED, (partial,)),
            (StockDocumentStatus.CANCELLED, (partial,)),
            (StockDocumentStatus.PARTIALLY_EXECUTED, (self.planned_line,)),
            (StockDocumentStatus.PARTIALLY_EXECUTED, (full,)),
            (StockDocumentStatus.COMPLETED, (partial,)),
        ):
            with (
                self.subTest(status=status),
                self.assertRaises(InvalidStockDocumentValueError),
            ):
                self.restore_document(self.document, status=status, lines=lines)
        for status in (
            StockDocumentStatus.PARTIALLY_EXECUTED,
            StockDocumentStatus.COMPLETED,
        ):
            with (
                self.subTest(status=status),
                self.assertRaises(EmptyStockDocumentError),
            ):
                self.restore_document(self.document, status=status, lines=())
        self.assertEqual(
            self.restore_document(
                self.document,
                status=StockDocumentStatus.PARTIALLY_EXECUTED,
                lines=(partial,),
            )
            .lines[0]
            .remaining_qty.value,
            Decimal(60),
        )
        with self.assertRaises(InvalidStockDocumentLineError):
            replace(
                self.planned_line, executed_qty=QuantityVO(Decimal(101))
            ).ensure_valid()

    def test_decimal_arithmetic_is_exact_during_grouping_registration_and_remaining(
        self,
    ) -> None:
        """Группировка и прогресс не зависят от внешних precision/traps и не округляют количества."""
        self.prepare(plan="100000000000000000000")
        lines = (self.line("12345678901234567890.05"), self.line("0.05"))
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            execution = self.create(lines=lines)
            document = self.document.register_execution(
                execution.snapshot_for_document(), updated_at=self.at(4)
            )
            self.assertEqual(
                document.lines[0].executed_qty.value, Decimal("12345678901234567890.10")
            )
            self.assertEqual(
                document.lines[0].remaining_qty.value,
                Decimal("87654321098765432109.90"),
            )
            self.assertFalse(any(context.flags.values()))

    def test_immutability_and_failure_leave_document_and_execution_unchanged(
        self,
    ) -> None:
        """Все переходы возвращают новые экземпляры; ошибочная регистрация не меняет накопленный прогресс."""
        execution = self.create()
        snapshot = execution.snapshot_for_document()
        invalid = replace(
            snapshot,
            lines=(replace(snapshot.lines[0], quantity=QuantityVO(Decimal(101))),),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.document.register_execution(invalid, updated_at=self.at(4))
        self.assertEqual(self.document.version, 2)
        self.assertEqual(self.document.lines[0].executed_qty.value, Decimal(0))
        for obj, field, value in (
            (execution, "document_version", 0),
            (execution.lines[0], "quantity", QuantityVO(Decimal(5))),
            (snapshot, "lines", ()),
            (execution.lines[0].route, "destination", self.dimensions),
        ):
            with self.subTest(obj=type(obj)), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)

    def test_execution_and_registration_do_not_post_or_change_physical_positions(
        self,
    ) -> None:
        """Новый Domain-срез не обходит будущую политику построения Ledger и атомарное сохранение."""
        with (
            patch(
                "src.modules.inventory.domain.stock_posting.aggregate.StockPosting.create",
                side_effect=RuntimeError("Не проводить"),
            ),
            patch(
                "src.modules.inventory.domain.stock_position.aggregate.StockPosition.apply_delta",
                side_effect=RuntimeError("Не менять остаток"),
            ),
        ):
            execution = self.create()
            document = self.document.register_execution(
                execution.snapshot_for_document(), updated_at=self.at(4)
            )
        self.assertEqual(document.lines[0].executed_qty.value, Decimal(10))
        self.assertNotIn("executions", document.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
