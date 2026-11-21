"""Автоматическое назначение всех фактических строк отгрузке через сохранённые основания складского документа."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_shipment_document_domain as document_fixture

from src.modules.inventory.domain.error import (
    InventoryError,
    StockQuantityArithmeticError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.shipment_execution import (
    ShipmentExecutionPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_reservation import (
    StockExecutionReservationPolicy,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentExecutionPlanSnapshotError,
    ShipmentExecutionMismatchError,
    ShipmentQuantityExceededError,
    ShipmentStatusError,
    ShipmentTimeError,
    ShipmentVersionConflictError,
)
from src.modules.inventory.domain.shipment.value_object.execution_binding import (
    ShipmentExecutionBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.shipment.registration_snapshot import (
    ShipmentExecutionRegistrationSnapshot,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentContextError,
    InvalidStockDocumentShipmentSnapshotError,
    StaleStockDocumentVersionError,
    StockDocumentExecutionNotAllowedError,
    StockDocumentOverExecutionError,
    StockDocumentShipmentMismatchError,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionShipmentSnapshotError,
    InvalidStockExecutionValueError,
    StockExecutionTimeError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentDocumentExecutionDomainTests(unittest.TestCase):
    """Проверяет документный и отгрузочный лимиты, три версии и производные назначения резервам."""

    def setUp(self) -> None:
        """Готовит Shipment v4 с остатком 1+1 KG, подтверждённый документ v1 и первый факт 0.5 KG по A."""
        self.fixture = document_fixture.ShipmentDocumentDomainTests()
        self.fixture.setUp()
        self.stock = self.fixture.f
        self.flow = self.fixture.flow
        self.time = self.fixture.time
        self.shipment = self.fixture.shipment
        self.document = self.fixture.confirm(self.fixture.build())
        self.a_line = next(
            line
            for line in self.document.lines
            if line.source.reference == str(self.stock.line_a.id.uuid)
        )
        self.b_line = next(
            line
            for line in self.document.lines
            if line.source.reference == str(self.stock.line_b.id.uuid)
        )
        self.execution = self.fact()

    def fact(
        self,
        document: StockDocument | None = None,
        rows: tuple[tuple[StockDocumentLineIdVO, str], ...] | None = None,
        *,
        uom: str = "KG",
        executed_at: datetime | None = None,
    ) -> StockExecution:
        """Создаёт полноценное исполнение через существующие фабрики документа и физического контекста."""
        document = self.document if document is None else document
        rows = ((self.a_line.id, "0.5"),) if rows is None else rows
        lines = tuple(
            StockExecutionLine.create(
                identifier=StockExecutionLineIdVO(uuid4()),
                document_line_id=identifier,
                inventory_item=self.stock.item.execution_snapshot(),
                quantity=QuantityVO(Decimal(amount)),
                uom=UomCodeVO(uom),
                route=IssueExecutionRouteVO(self.flow.position.dimensions),
            )
            for identifier, amount in rows
        )
        return StockExecution.create(
            identifier=StockExecutionIdVO(uuid4()),
            document=document.execution_snapshot(),
            executed_at=self.time if executed_at is None else executed_at,
            lines=lines,
            warehouse=self.stock.warehouse,
            inventory_items=(self.stock.item.execution_snapshot(),),
            locations=(self.flow.location,),
        )

    def build(self, **changes: object) -> ShipmentExecutionRegistrationSnapshot:
        """Строит регистрацию по трём специализированным снимкам без ручных привязок."""
        return ShipmentExecutionPolicy.build_registration_from_document(
            **(
                dict(
                    shipment=self.shipment.execution_snapshot(),
                    document=self.document.shipment_snapshot(),
                    execution=self.execution.shipment_snapshot(),
                )
                | changes
            )
        )

    def test_getters_are_purpose_specific_frozen_and_decode_sources_to_typed_ids(
        self,
    ) -> None:
        """Геттер документа выводит типизированные ссылки, а геттер факта сохраняет документную версию и строки."""
        document, execution = (
            self.document.shipment_snapshot(),
            self.execution.shipment_snapshot(),
        )
        document.ensure_valid()
        execution.ensure_valid()
        self.assertEqual(
            (
                document.id,
                document.version,
                document.shipment_id,
                document.source_shipment_version,
            ),
            (self.document.id, 1, self.shipment.id, 4),
        )
        self.assertEqual(
            {line.shipment_line_id for line in document.lines},
            {line.id for line in self.shipment.lines},
        )
        self.assertEqual(
            (
                execution.document_id,
                execution.document_version,
                execution.lines[0].document_line_id,
            ),
            (self.document.id, 1, self.a_line.id),
        )
        self.assertFalse(hasattr(execution.lines[0], "route"))
        self.assertFalse(hasattr(document.lines[0], "source"))
        for snapshot in (document, execution):
            with self.assertRaises(FrozenInstanceError):
                snapshot.lines = ()
        self.assertFalse(hasattr(self.execution.reservation_snapshot(), "document_id"))

    def test_producers_validate_complete_roots_and_generic_documents_are_rejected(
        self,
    ) -> None:
        """Геттеры не маскируют повреждённую историю и не выдают обычный документ за документ Shipment."""
        generic = StockDocument.create(
            identifier=StockDocumentIdVO(uuid4()),
            operation_type=StockOperationType.ISSUE,
            warehouse=self.stock.warehouse,
            owner_id=self.stock.owner,
            created_at=self.time,
        )
        with self.assertRaises(StockDocumentShipmentMismatchError):
            generic.shipment_snapshot()
        with self.assertRaises(StockDocumentShipmentMismatchError):
            replace(self.document, source=None).shipment_snapshot()
        with self.assertRaises(StockDocumentShipmentMismatchError):
            replace(
                self.document,
                lines=(
                    replace(
                        self.a_line,
                        source=DocumentLineSourceVO("inventory.shipment_line", "bad"),
                    ),
                ),
            ).shipment_snapshot()
        with self.assertRaises(InvalidStockExecutionValueError):
            replace(self.execution, document_version=True).shipment_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                self.execution, lines=(replace(self.execution.lines[0], route=None),)
            ).shipment_snapshot()

    def test_automatic_result_equals_existing_manual_assignment(self) -> None:
        """Автоматическая ветка сохраняет прежние суммы, время факта, версии и назначение резерва A."""
        result = self.build()
        manual = ShipmentExecutionPolicy.build_registration(
            shipment=self.shipment.execution_snapshot(),
            execution=self.execution.reservation_snapshot(),
            bindings=(
                ShipmentExecutionBindingVO(
                    self.execution.lines[0].id, self.stock.line_a.id
                ),
            ),
        )
        self.assertEqual(result, manual)
        self.assertEqual(result.lines[0].quantity.value, Decimal("0.5"))
        self.assertEqual(result.lines[0].reservation_id, self.stock.a.id)

    def test_two_partial_executions_preserve_origin_version_while_advancing_both_roots(
        self,
    ) -> None:
        """Основание v4 сохраняется при исполнениях по документам v1/v2 и Shipment v4/v5."""
        first = self.build()
        shipment_after = self.shipment.register_execution(
            first, expected_version=4, updated_at=self.time
        )
        document_after = self.document.register_execution(
            self.execution.snapshot_for_document(), updated_at=self.time
        )
        self.assertEqual(
            (
                shipment_after.status,
                shipment_after.version,
                document_after.status,
                document_after.version,
            ),
            (
                ShipmentStatus.PARTIALLY_SHIPPED,
                5,
                StockDocumentStatus.PARTIALLY_EXECUTED,
                2,
            ),
        )
        second = self.fact(
            document_after, ((self.a_line.id, "0.5"), (self.b_line.id, "1"))
        )
        result = self.build(
            shipment=shipment_after.execution_snapshot(),
            document=document_after.shipment_snapshot(),
            execution=second.shipment_snapshot(),
        )
        self.assertEqual(result.shipment_version, 5)
        full = shipment_after.register_execution(
            result, expected_version=5, updated_at=self.time
        )
        document_full = document_after.register_execution(
            second.snapshot_for_document(), updated_at=self.time
        )
        self.assertEqual(
            (full.status, full.version, document_full.status, document_full.version),
            (ShipmentStatus.SHIPPED, 6, StockDocumentStatus.COMPLETED, 3),
        )
        self.assertEqual(document_full.source.version, 4)
        self.assertEqual(document_full.shipment_snapshot().source_shipment_version, 4)
        self.assertTrue(
            all(line.shipped_qty == line.planned_qty for line in full.lines)
        )

    def test_multiple_actual_rows_share_document_line_and_all_are_assigned(
        self,
    ) -> None:
        """Несколько фактов одной плановой строки суммируются; другие неисполненные строки документа допустимы."""
        execution = self.fact(rows=((self.a_line.id, "0.25"), (self.a_line.id, "0.75")))
        result = self.build(execution=execution.shipment_snapshot())
        self.assertEqual(len(result.lines), 1)
        self.assertEqual(result.lines[0].quantity.value, Decimal(1))
        self.assertEqual(
            set(result.lines[0].execution_line_ids),
            {line.id for line in execution.lines},
        )
        self.assertEqual(len(result.reservation_bindings()), 2)
        self.assertEqual(
            self.build(
                execution=replace(
                    execution.shipment_snapshot(),
                    lines=tuple(reversed(execution.shipment_snapshot().lines)),
                )
            ),
            result,
        )
        snapshot = self.document.shipment_snapshot()
        self.assertEqual(
            self.build(
                document=replace(snapshot, lines=tuple(reversed(snapshot.lines))),
                execution=execution.shipment_snapshot(),
            ),
            result,
        )

    def test_actual_row_cannot_be_unknown_or_silently_ignored(self) -> None:
        """В отличие от ручной ветки автоматическая ветка назначает весь факт, включая каждую дополнительную строку."""
        snapshot = self.execution.shipment_snapshot()
        unknown = replace(
            snapshot.lines[0],
            execution_line_id=StockExecutionLineIdVO(uuid4()),
            document_line_id=StockDocumentLineIdVO(uuid4()),
        )
        with self.assertRaises(InvalidStockDocumentContextError):
            self.build(execution=replace(snapshot, lines=(*snapshot.lines, unknown)))

    def test_every_document_origin_must_belong_to_current_shipment_even_if_unused(
        self,
    ) -> None:
        """Постороннее основание в неисполняемой строке документа тоже делает контекст несовместимым."""
        snapshot = self.document.shipment_snapshot()
        for changes in (
            dict(shipment_line_id=ShipmentLineIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            lines = tuple(
                (
                    replace(line, **changes)
                    if line.document_line_id == self.b_line.id
                    else line
                )
                for line in snapshot.lines
            )
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(document=replace(snapshot, lines=lines))

    def test_each_actual_item_and_unit_are_checked_before_grouping(self) -> None:
        """Нельзя скрыть несовместимый товар или единицу внутри суммы нескольких фактов одной строки."""
        execution = self.fact(
            rows=((self.a_line.id, "0.25"), (self.a_line.id, "0.25"))
        ).shipment_snapshot()
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                self.build(
                    execution=replace(
                        execution,
                        lines=(
                            execution.lines[0],
                            replace(execution.lines[1], **changes),
                        ),
                    )
                )

    def test_document_identity_and_fact_version_are_mandatory(self) -> None:
        """Факт принимается по тому документу и той версии, по которым он был создан."""
        snapshot = self.execution.shipment_snapshot()
        with self.assertRaises(InvalidStockDocumentContextError):
            self.build(
                execution=replace(snapshot, document_id=StockDocumentIdVO(uuid4()))
            )
        for version in (0, 2):
            with self.assertRaises(StaleStockDocumentVersionError):
                self.build(execution=replace(snapshot, document_version=version))
        after = self.document.register_execution(
            self.execution.snapshot_for_document(), updated_at=self.time
        )
        with self.assertRaises(StaleStockDocumentVersionError):
            self.build(document=after.shipment_snapshot())

    def test_origin_identity_and_future_version_are_rejected_but_older_version_is_valid(
        self,
    ) -> None:
        """Версия основания историческая: допустима старая, но не версия выше текущего Shipment."""
        snapshot = self.document.shipment_snapshot()
        with self.assertRaises(ShipmentExecutionMismatchError):
            self.build(document=replace(snapshot, shipment_id=ShipmentIdVO(uuid4())))
        with self.assertRaises(ShipmentVersionConflictError):
            self.build(document=replace(snapshot, source_shipment_version=5))
        self.assertEqual(
            self.build(
                document=replace(snapshot, source_shipment_version=3)
            ).shipment_version,
            4,
        )

    def test_operation_and_all_scope_combinations_are_checked(self) -> None:
        """Три участника должны относиться к одному складу/владельцу; автоматическая отгрузка использует ISSUE."""
        document = self.document.shipment_snapshot()
        execution = self.execution.shipment_snapshot()
        for field, value in (
            ("warehouse_id", WarehouseIdVO(uuid4())),
            ("owner_id", StockOwnerIdVO(uuid4())),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                self.build(execution=replace(execution, **{field: value}))
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(
                    document=replace(document, **{field: value}),
                    execution=replace(execution, **{field: value}),
                )
        for operation in (StockOperationType.RECEIPT, StockOperationType.INTERNAL_MOVE):
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(execution=replace(execution, operation_type=operation))

    def test_only_confirmed_and_partial_document_states_are_executable(self) -> None:
        """Черновик, отмена и полное исполнение документа не подходят для новой регистрации."""
        snapshot = self.document.shipment_snapshot()
        for status in (
            StockDocumentStatus.DRAFT,
            StockDocumentStatus.CANCELLED,
            StockDocumentStatus.COMPLETED,
        ):
            lines = (
                tuple(
                    replace(line, executed_qty=line.planned_qty)
                    for line in snapshot.lines
                )
                if status is StockDocumentStatus.COMPLETED
                else snapshot.lines
            )
            with self.assertRaises(StockDocumentExecutionNotAllowedError):
                self.build(document=replace(snapshot, status=status, lines=lines))

    def test_only_confirmed_and_partial_shipment_states_are_executable(self) -> None:
        """Документное подтверждение не открывает исполнение черновика, отмены или завершённого Shipment."""
        snapshot = self.shipment.execution_snapshot()
        for status in (
            ShipmentStatus.DRAFT,
            ShipmentStatus.CANCELLED,
            ShipmentStatus.SHIPPED,
        ):
            lines = tuple(
                replace(
                    line,
                    shipped_qty=(
                        line.planned_qty
                        if status is ShipmentStatus.SHIPPED
                        else QuantityVO(Decimal(0))
                    ),
                )
                for line in snapshot.lines
            )
            with self.assertRaises(ShipmentStatusError):
                self.build(shipment=replace(snapshot, status=status, lines=lines))

    def test_document_limit_is_checked_independently_of_shipment_limit(self) -> None:
        """Факт 0.5 KG превышает документный остаток 0.4 KG, хотя отправление допускает 1 KG."""
        snapshot = self.document.shipment_snapshot()
        rows = tuple(
            (
                replace(line, planned_qty=QuantityVO(Decimal("0.4")))
                if line.document_line_id == self.a_line.id
                else line
            )
            for line in snapshot.lines
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(document=replace(snapshot, lines=rows))
        facts = self.execution.shipment_snapshot()
        lines = (
            replace(facts.lines[0], quantity=QuantityVO(Decimal("0.6"))),
            replace(
                facts.lines[0],
                execution_line_id=StockExecutionLineIdVO(uuid4()),
                quantity=QuantityVO(Decimal("0.6")),
            ),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(execution=replace(facts, lines=lines))

    def test_shipment_limit_is_checked_independently_of_document_limit(self) -> None:
        """Документ допускает факт 0.5 KG, но актуальный остаток отправления может быть только 0.25 KG."""
        snapshot = self.shipment.execution_snapshot()
        lines = tuple(
            (
                replace(line, shipped_qty=QuantityVO(Decimal("2.75")))
                if line.id == self.stock.line_a.id
                else line
            )
            for line in snapshot.lines
        )
        with self.assertRaises(ShipmentQuantityExceededError):
            self.build(shipment=replace(snapshot, version=5, lines=lines))

    def test_document_accumulated_progress_is_used_in_remaining_limit(self) -> None:
        """Учитывается уже исполненное количество документа, а не только первоначальный план строки."""
        snapshot = self.document.shipment_snapshot()
        lines = tuple(
            (
                replace(line, executed_qty=QuantityVO(Decimal("0.75")))
                if line.document_line_id == self.a_line.id
                else line
            )
            for line in snapshot.lines
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(
                document=replace(
                    snapshot, status=StockDocumentStatus.PARTIALLY_EXECUTED, lines=lines
                )
            )

    def test_fact_time_must_follow_both_document_and_shipment_states(self) -> None:
        """Проверяются обе независимые хронологии; время берётся из факта без дополнительного пользовательского ввода."""
        with self.assertRaises(StockExecutionTimeError):
            self.build(
                document=replace(
                    self.document.shipment_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                )
            )
        with self.assertRaises(ShipmentTimeError):
            self.build(
                shipment=replace(
                    self.shipment.execution_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                )
            )
        snapshot = self.execution.shipment_snapshot()
        with self.assertRaises(StockExecutionTimeError):
            self.build(
                execution=replace(
                    snapshot, executed_at=self.time - timedelta(seconds=1)
                )
            )

    def test_document_snapshot_revalidates_own_types_versions_links_and_progress(
        self,
    ) -> None:
        """Снимок документа не доверяет аннотациям, bool-версиям и повторным основаниям строк."""
        snapshot = self.document.shipment_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(version=True),
            dict(version=-1),
            dict(status="CONFIRMED"),
            dict(operation_type=StockOperationType.RECEIPT),
            dict(warehouse_id=None),
            dict(owner_id=uuid4()),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(shipment_id=uuid4()),
            dict(source_shipment_version=True),
            dict(source_shipment_version=-1),
            dict(lines=[]),
            dict(lines=(None,)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
        ):
            with self.assertRaises(InvalidStockDocumentShipmentSnapshotError):
                self.build(document=replace(snapshot, **changes))
        row = snapshot.lines[0]
        for changes in (
            dict(document_line_id=uuid4()),
            dict(shipment_line_id=None),
            dict(inventory_item_id=None),
            dict(base_uom=None),
            dict(planned_qty=QuantityVO(Decimal(0))),
            dict(executed_qty=None),
            dict(executed_qty=QuantityVO(Decimal(2))),
        ):
            with self.assertRaises(InvalidStockDocumentShipmentSnapshotError):
                self.build(document=replace(snapshot, lines=(replace(row, **changes),)))
        with self.assertRaises(InvalidStockDocumentShipmentSnapshotError):
            self.build(
                document=replace(
                    snapshot,
                    lines=(
                        row,
                        replace(
                            snapshot.lines[1], shipment_line_id=row.shipment_line_id
                        ),
                    ),
                )
            )
        for changes in (dict(lines=()), dict(status=StockDocumentStatus.COMPLETED)):
            with self.assertRaises(InventoryError):
                self.build(document=replace(snapshot, **changes))

    def test_execution_snapshot_revalidates_types_version_time_and_unique_fact_ids(
        self,
    ) -> None:
        """Несколько фактических ID на одну строку документа допустимы, повтор одного фактического ID — нет."""
        snapshot = self.execution.shipment_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(document_id=uuid4()),
            dict(document_version=True),
            dict(document_version=-1),
            dict(operation_type="ISSUE"),
            dict(warehouse_id=None),
            dict(owner_id=None),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=()),
            dict(lines=(None,)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
        ):
            with self.assertRaises(InvalidStockExecutionShipmentSnapshotError):
                self.build(execution=replace(snapshot, **changes))
        row = snapshot.lines[0]
        for changes in (
            dict(execution_line_id=uuid4()),
            dict(document_line_id=None),
            dict(inventory_item_id=None),
            dict(base_uom=None),
            dict(quantity=QuantityVO(Decimal(0))),
            dict(quantity=Decimal(1)),
        ):
            with self.assertRaises(InvalidStockExecutionShipmentSnapshotError):
                self.build(
                    execution=replace(snapshot, lines=(replace(row, **changes),))
                )

    def test_wrong_purpose_and_full_roots_cannot_replace_specialized_snapshots(
        self,
    ) -> None:
        """Автоматическая ветка принимает только три соответствующих контракта Domain-снимков."""
        for value in (None, self.document, self.document.execution_snapshot()):
            with self.assertRaises(InvalidStockDocumentShipmentSnapshotError):
                self.build(document=value)
        for value in (None, self.execution, self.execution.reservation_snapshot()):
            with self.assertRaises(InvalidStockExecutionShipmentSnapshotError):
                self.build(execution=value)
        for value in (None, self.shipment, self.shipment.document_snapshot()):
            with self.assertRaises(InvalidShipmentExecutionPlanSnapshotError):
                self.build(shipment=value)

    def test_registration_and_consumptions_share_derived_quantities_and_reservations(
        self,
    ) -> None:
        """Из автоматического результата получается погашение только резерва A на фактические 0.5 KG."""
        registration = self.build()
        consumptions = StockExecutionReservationPolicy.build_consumptions(
            execution=self.execution.reservation_snapshot(),
            bindings=registration.reservation_bindings(),
            reservations=(self.stock.a.execution_snapshot(),),
        )
        self.assertEqual(len(consumptions), 1)
        self.assertEqual(
            (consumptions[0].reservation_id, consumptions[0].quantity.value),
            (self.stock.a.id, Decimal("0.5")),
        )
        a = self.stock.a.consume_execution(
            consumptions[0],
            expected_version=self.stock.a.version,
            inventory_item=self.stock.item.stock_snapshot(),
            updated_at=self.time,
        )
        position = self.flow.position.apply_delta(
            StockDeltaVO(Decimal("-0.5")),
            inventory_item=self.stock.item.stock_snapshot(),
            location=self.flow.location,
            warehouse=self.stock.warehouse,
        )
        pool = self.stock.pool.consume_reservations(
            consumptions,
            expected_version=self.stock.pool.version,
            inventory_item=self.stock.item.availability_snapshot(),
            warehouse=self.stock.warehouse,
            as_of=self.time.date(),
            positions=(position.availability_snapshot(),),
            locations=(self.flow.location,),
        )
        self.assertEqual(
            (a.reserved_qty.value, a.consumed_qty.value, pool.reserved_qty.value),
            (Decimal("3.5"), Decimal("0.5"), Decimal("6.5")),
        )
        self.assertEqual(self.stock.b.reserved_qty.value, Decimal(3))

    def test_gram_input_remains_exact_base_quantity_without_reconversion(self) -> None:
        """Факт 500 G уже содержит 0.5 KG; автоматическая связь не пересчитывает его повторно."""
        execution = self.fact(rows=((self.a_line.id, "500"),), uom="G")
        result = self.build(execution=execution.shipment_snapshot())
        self.assertEqual(result.lines[0].quantity.value, Decimal("0.5"))
        self.assertEqual(execution.lines[0].conversion.uom, UomCodeVO("G"))

    def test_exact_grouping_is_independent_of_decimal_context(self) -> None:
        """Документная и отгрузочная группировки используют точную общую арифметику."""
        execution = self.fact(rows=((self.a_line.id, "0.45"), (self.a_line.id, "0.55")))
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = self.build(execution=execution.shipment_snapshot())
            self.assertEqual(result.lines[0].quantity.value, Decimal(1))

    def test_unrepresentable_fact_group_has_controlled_arithmetic_error(self) -> None:
        """Общий защитный предел сохраняется при документном суммировании фактических строк."""
        snapshot = self.execution.shipment_snapshot()
        row = snapshot.lines[0]
        lines = (
            replace(row, quantity=QuantityVO(Decimal("1E+1000001"))),
            replace(row, execution_line_id=StockExecutionLineIdVO(uuid4())),
        )
        with self.assertRaises(StockQuantityArithmeticError):
            self.build(execution=replace(snapshot, lines=lines))

    def test_registration_uses_current_shipment_version_and_old_result_cannot_be_reapplied(
        self,
    ) -> None:
        """Результат фиксирует текущую версию прогресса, а не историческую версию основания документа."""
        shipment = replace(self.shipment, version=9)
        result = self.build(shipment=shipment.execution_snapshot())
        self.assertEqual(result.shipment_version, 9)
        after = shipment.register_execution(
            result, expected_version=9, updated_at=self.time
        )
        with self.assertRaises(ShipmentVersionConflictError):
            after.register_execution(
                result, expected_version=after.version, updated_at=self.time
            )

    def test_automatic_builder_does_not_modify_inputs_on_success_or_failure(
        self,
    ) -> None:
        """Policy только строит результат; исходные корни и основания остаются неизменными."""
        before = (
            self.shipment,
            self.document,
            self.execution,
            self.stock.a,
            self.stock.pool,
        )
        self.build()
        with self.assertRaises(ShipmentExecutionMismatchError):
            self.build(
                document=replace(
                    self.document.shipment_snapshot(), shipment_id=ShipmentIdVO(uuid4())
                )
            )
        self.assertEqual(
            (
                self.shipment,
                self.document,
                self.execution,
                self.stock.a,
                self.stock.pool,
            ),
            before,
        )

    def test_serial_and_lot_serial_facts_are_assigned_by_document_line_without_reselection(
        self,
    ) -> None:
        """Два индивидуальных факта по 1 PCS завершают остатки SERIAL/LOT_AND_SERIAL без повторного выбора резервов."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = replace(
                self.stock.item,
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
            )
            shipment = replace(
                self.shipment,
                lines=tuple(
                    replace(
                        line,
                        base_uom=item.base_uom,
                        conversion=replace(line.conversion, uom=item.base_uom),
                    )
                    for line in self.shipment.lines
                ),
            )
            document = replace(
                self.document,
                lines=tuple(
                    replace(
                        line,
                        base_uom=item.base_uom,
                        conversion=replace(line.conversion, uom=item.base_uom),
                    )
                    for line in self.document.lines
                ),
            )
            lot_id = (
                StockLotIdVO(uuid4()) if mode is TrackingMode.LOT_AND_SERIAL else None
            )
            lines = tuple(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=line.id,
                    inventory_item=item.execution_snapshot(),
                    quantity=line.planned_qty,
                    uom=item.base_uom,
                    route=IssueExecutionRouteVO(
                        replace(
                            self.flow.position.dimensions,
                            lot_id=lot_id,
                            serial_id=StockSerialIdVO(uuid4()),
                        )
                    ),
                )
                for line in document.lines
            )
            execution = StockExecution.restore(
                identifier=StockExecutionIdVO(uuid4()),
                document_id=document.id,
                document_version=document.version,
                operation_type=StockOperationType.ISSUE,
                warehouse_id=document.warehouse_id,
                owner_id=document.owner_id,
                executed_at=self.time,
                lines=lines,
            )
            registration = self.build(
                shipment=shipment.execution_snapshot(),
                document=document.shipment_snapshot(),
                execution=execution.shipment_snapshot(),
            )
            full = shipment.register_execution(
                registration, expected_version=4, updated_at=self.time
            )
            self.assertEqual(full.status, ShipmentStatus.SHIPPED)
            self.assertEqual(
                {
                    binding.reservation_id
                    for binding in registration.reservation_bindings()
                },
                {self.stock.a.id, self.stock.b.id},
            )

    def test_complete_flow_applies_two_partial_facts_to_progress_reservations_and_pool(
        self,
    ) -> None:
        """Согласованное состояние после 2+1 KG завершается двумя фактами, оставляя лишнее удержание 1+1 KG."""
        item = self.stock.item
        a = self.stock.a.consume(
            QuantityVO(Decimal(2)),
            expected_version=self.stock.a.version,
            inventory_item=item.stock_snapshot(),
            consumed_at=self.time,
            updated_at=self.time,
        )
        b = self.stock.b.consume(
            QuantityVO(Decimal(1)),
            expected_version=self.stock.b.version,
            inventory_item=item.stock_snapshot(),
            consumed_at=self.time,
            updated_at=self.time,
        )
        position = self.flow.position.apply_delta(
            StockDeltaVO(Decimal(-3)),
            inventory_item=item.stock_snapshot(),
            location=self.flow.location,
            warehouse=self.stock.warehouse,
        )
        pool = self.stock.pool.consume_reserved(
            QuantityVO(Decimal(3)),
            expected_version=self.stock.pool.version,
            inventory_item=item.availability_snapshot(),
            warehouse=self.stock.warehouse,
            as_of=self.time.date(),
            positions=(position.availability_snapshot(),),
            locations=(self.flow.location,),
        )
        shipment, document = self.shipment, self.document
        for index in range(2):
            execution = (
                self.execution
                if index == 0
                else self.fact(
                    document, ((self.a_line.id, "0.5"), (self.b_line.id, "1"))
                )
            )
            registration = self.build(
                shipment=shipment.execution_snapshot(),
                document=document.shipment_snapshot(),
                execution=execution.shipment_snapshot(),
            )
            current = {a.id: a, b.id: b}
            used = {
                binding.reservation_id
                for binding in registration.reservation_bindings()
            }
            consumptions = StockExecutionReservationPolicy.build_consumptions(
                execution=execution.reservation_snapshot(),
                bindings=registration.reservation_bindings(),
                reservations=tuple(
                    current[identifier].execution_snapshot() for identifier in used
                ),
            )
            for consumption in consumptions:
                reservation = current[consumption.reservation_id]
                current[reservation.id] = reservation.consume_execution(
                    consumption,
                    expected_version=reservation.version,
                    inventory_item=item.stock_snapshot(),
                    updated_at=self.time,
                )
            a, b = current[a.id], current[b.id]
            delta = sum(
                (line.quantity.value for line in execution.lines), Decimal(0)
            ).copy_negate()
            position = position.apply_delta(
                StockDeltaVO(delta),
                inventory_item=item.stock_snapshot(),
                location=self.flow.location,
                warehouse=self.stock.warehouse,
            )
            pool = pool.consume_reservations(
                consumptions,
                expected_version=pool.version,
                inventory_item=item.availability_snapshot(),
                warehouse=self.stock.warehouse,
                as_of=self.time.date(),
                positions=(position.availability_snapshot(),),
                locations=(self.flow.location,),
            )
            shipment = shipment.register_execution(
                registration, expected_version=shipment.version, updated_at=self.time
            )
            document = document.register_execution(
                execution.snapshot_for_document(), updated_at=self.time
            )
        self.assertEqual(
            (shipment.status, shipment.version, document.status, document.version),
            (ShipmentStatus.SHIPPED, 6, StockDocumentStatus.COMPLETED, 3),
        )
        self.assertEqual(
            (
                a.reserved_qty.value,
                a.consumed_qty.value,
                b.reserved_qty.value,
                b.consumed_qty.value,
            ),
            (Decimal(1), Decimal(3), Decimal(1), Decimal(2)),
        )
        self.assertEqual(
            (
                position.on_hand_qty.value,
                pool.eligible_qty.value,
                pool.reserved_qty.value,
            ),
            (Decimal(5), Decimal(5), Decimal(2)),
        )
        self.assertEqual(document.source.version, 4)


if __name__ == "__main__":
    unittest.main()
