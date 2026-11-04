"""Документы отправки StockTransfer: происхождение, согласованная пара и свежесть основания при подтверждении."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_stock_transfer_dispatch_domain as dispatch_fixture
from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.policy.stock_transfer_dispatch_document import (
    StockTransferDispatchDocumentPolicy,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentTransferDispatchSnapshotError,
    InvalidStockTransferDispatchDocumentLineBindingError,
    StockDocumentTransferDispatchMismatchError,
    StaleStockTransferDocumentSourceError,
    StockDocumentTransferDispatchQuantityExceededError,
    UnbalancedStockTransferDispatchDocumentsError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
    StockDocumentNotDraftError,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
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
from src.modules.inventory.domain.stock_document.value_object.transfer_dispatch_line_binding import (
    StockTransferDispatchDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_document.transfer_dispatch_snapshot import (
    StockDocumentTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferDispatchDocumentSnapshotError,
    InvalidStockTransferValueError,
    StockTransferStatusError,
    StockTransferTransitMismatchError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferDocumentDomainTests(unittest.TestCase):
    """Проверяет самостоятельные планы ISSUE A и RECEIPT T без изменения StockTransfer или физических остатков."""

    def setUp(self) -> None:
        """Готовит подтверждённые 50 KG, три активных склада и две новые стороны одного основания."""
        self.d = dispatch_fixture.StockTransferDispatchDomainTests()
        self.d.setUp()
        self.transfer = self.d.transfer
        self.time = self.d.time
        self.bindings = self.new_bindings()
        self.issue = self.build(StockOperationType.ISSUE)
        self.receipt = self.build(StockOperationType.RECEIPT)

    def new_bindings(self) -> tuple[StockTransferDispatchDocumentLineBindingVO, ...]:
        """Передаёт ровно все открытые строки и разные новые ID обеих сторон извне Domain."""
        return tuple(
            StockTransferDispatchDocumentLineBindingVO(
                line.transfer_line_id,
                StockDocumentLineIdVO(uuid4()),
                StockDocumentLineIdVO(uuid4()),
            )
            for line in self.transfer.dispatch_document_snapshot().lines
        )

    def build(
        self,
        operation_type: StockOperationType = StockOperationType.ISSUE,
        **changes: object,
    ) -> StockDocument:
        """Строит выбранную сторону пары по одному снимку остатка и общему назначению новых ID."""
        return StockDocument.create_from_stock_transfer_dispatch(
            **(
                dict(
                    identifier=StockDocumentIdVO(uuid4()),
                    operation_type=operation_type,
                    transfer=self.transfer.dispatch_document_snapshot(),
                    source_warehouse=self.d.f.source,
                    destination_warehouse=self.d.f.destination,
                    transit_warehouse=self.d.transit_warehouse,
                    inventory_items=(self.d.f.item.document_snapshot(),),
                    line_bindings=self.bindings,
                    created_at=self.time,
                )
                | changes
            )
        )

    def confirm(self, document: StockDocument, **changes: object) -> StockDocument:
        """Подтверждает один корень по свежему основанию и снимку другой стороны, не меняя их."""
        issue = document.operation_type is StockOperationType.ISSUE
        companion = self.receipt if issue else self.issue
        return document.confirm(
            **(
                dict(
                    transfer=self.transfer.dispatch_document_snapshot(),
                    companion_document=companion.transfer_dispatch_snapshot(),
                    transfer_warehouses=(
                        self.d.f.source,
                        self.d.f.destination,
                        self.d.transit_warehouse,
                    ),
                    warehouse=self.d.f.source if issue else self.d.transit_warehouse,
                    inventory_items=(self.d.f.item.document_snapshot(),),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def restore(self, document: StockDocument, **changes: object) -> StockDocument:
        """Восстанавливает полный собственный состав без свежего перемещения, склада или парного документа."""
        return StockDocument.restore(
            **(
                dict(
                    identifier=document.id,
                    operation_type=document.operation_type,
                    warehouse_id=document.warehouse_id,
                    owner_id=document.owner_id,
                    source=document.source,
                    status=document.status,
                    lines=document.lines,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    version=document.version,
                )
                | changes
            )
        )

    def change(self, document: StockDocument, value: str = "20") -> StockDocument:
        """Меняет количество черновика через его метод с сохранением основания строки."""
        return document.change_line(
            identifier=document.lines[0].id,
            quantity=QuantityVO(Decimal(value)),
            uom=self.d.f.item.base_uom,
            inventory_item=self.d.f.item.document_snapshot(),
            updated_at=self.time,
        )

    def execution(self, document: StockDocument, value: str) -> StockExecution:
        """Создаёт реальный частичный факт существующим путём документа и активной локации."""
        issue = document.operation_type is StockOperationType.ISSUE
        dimensions = self.d.source_dimensions if issue else self.d.transit_dimensions
        line = StockExecutionLine.create(
            identifier=StockExecutionLineIdVO(uuid4()),
            document_line_id=document.lines[0].id,
            inventory_item=self.d.f.item.execution_snapshot(),
            quantity=QuantityVO(Decimal(value)),
            uom=self.d.f.item.base_uom,
            route=(
                IssueExecutionRouteVO(dimensions)
                if issue
                else ReceiptExecutionRouteVO(dimensions)
            ),
        )
        return StockExecution.create(
            identifier=StockExecutionIdVO(uuid4()),
            document=document.execution_snapshot(),
            executed_at=self.time,
            lines=(line,),
            warehouse=self.d.f.source if issue else self.d.transit_warehouse,
            inventory_items=(self.d.f.item.execution_snapshot(),),
            locations=(self.d.source_location if issue else self.d.transit_location,),
        )

    def test_build_pair_creates_separate_drafts_with_equal_base_plans_and_zero_progress(
        self,
    ) -> None:
        """Два плана на 50 KG имеют отдельные ID и версии 0, не удваивая физический запас."""
        self.assertNotEqual(self.issue.id, self.receipt.id)
        for document, warehouse in (
            (self.issue, self.d.f.source),
            (self.receipt, self.d.transit_warehouse),
        ):
            self.assertEqual(
                (
                    document.status,
                    document.version,
                    document.warehouse_id,
                    document.owner_id,
                ),
                (StockDocumentStatus.DRAFT, 0, warehouse.id, self.transfer.owner_id),
            )
            line = document.lines[0]
            self.assertEqual(
                (
                    line.planned_qty.value,
                    line.executed_qty.value,
                    line.conversion.factor_to_base,
                ),
                (Decimal(50), Decimal(0), Decimal(1)),
            )
            self.assertEqual(
                (line.conversion.quantity, line.conversion.uom, line.sku),
                (line.planned_qty, UomCodeVO("KG"), self.d.f.item.sku),
            )
        self.assertEqual(
            self.issue.lines[0].id, self.bindings[0].issue_document_line_id
        )
        self.assertEqual(
            self.receipt.lines[0].id, self.bindings[0].receipt_document_line_id
        )
        self.assertEqual(
            (
                self.transfer.version,
                self.transfer.transit,
                self.transfer.lines[0].dispatched_qty.value,
            ),
            (2, None, Decimal(0)),
        )
        self.assertEqual(
            (
                self.d.source_position.on_hand_qty.value,
                self.d.transit_position.on_hand_qty.value,
            ),
            (Decimal(50), Decimal(0)),
        )
        self.assertEqual(
            self.transfer.lines[0].conversion.quantity.value, Decimal(50000)
        )

    def test_source_records_role_transfer_version_and_line_id(self) -> None:
        """Шапки различают роль пары, а обе строки ссылаются на одну TransferLine."""
        for document, system in (
            (self.issue, StockTransferDispatchDocumentPolicy.ISSUE_SOURCE_SYSTEM),
            (self.receipt, StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM),
        ):
            self.assertEqual(
                document.source,
                DocumentSourceVO(
                    system, str(self.transfer.id.uuid), self.transfer.version
                ),
            )
            self.assertEqual(
                document.lines[0].source,
                DocumentLineSourceVO(
                    StockTransferDispatchDocumentPolicy.LINE_SOURCE_SYSTEM,
                    str(self.transfer.lines[0].id.uuid),
                ),
            )
            self.assertEqual(
                document.transfer_dispatch_snapshot().source_transfer_version, 2
            )

    def test_binding_types_and_immutability_are_enforced(self) -> None:
        """VO не принимает сырые UUID и одинаковые ID строк разных сторон."""
        binding = self.bindings[0]
        for changes in (
            dict(transfer_line_id=uuid4()),
            dict(issue_document_line_id=None),
            dict(receipt_document_line_id=binding.issue_document_line_id),
        ):
            with self.assertRaises(
                InvalidStockTransferDispatchDocumentLineBindingError
            ):
                replace(binding, **changes)
        with self.assertRaises(FrozenInstanceError):
            binding.transfer_line_id = StockTransferLineIdVO(uuid4())
        with self.assertRaises(FrozenInstanceError):
            self.transfer.dispatch_document_snapshot().version = 10

    def test_build_requires_exact_unique_bindings_for_both_sides(self) -> None:
        """Нельзя пропустить строку, назначить чужую или повторить ID основания."""
        binding = self.bindings[0]
        for values in (
            (),
            self.bindings * 2,
            list(self.bindings),
            (None,),
            (replace(binding, transfer_line_id=StockTransferLineIdVO(uuid4())),),
        ):
            with self.assertRaises(
                InvalidStockTransferDispatchDocumentLineBindingError
            ):
                self.build(line_bindings=values)

    def test_cross_side_line_ids_are_unique_across_all_plan_lines(self) -> None:
        """Новый ID расхода другой строки не может совпасть с ID прихода первой."""
        second = self.d.f.new_line()
        self.transfer = self.d.f.confirm(self.d.f.add(self.d.f.add(), second))
        bindings = self.new_bindings()
        bindings = (
            bindings[0],
            replace(
                bindings[1], issue_document_line_id=bindings[0].receipt_document_line_id
            ),
        )
        with self.assertRaises(InvalidStockTransferDispatchDocumentLineBindingError):
            self.build(line_bindings=bindings)

    def test_same_item_in_distinct_transfer_lines_is_not_merged(self) -> None:
        """Один товар в двух обязательствах сохраняет два основания и две строки в каждой стороне."""
        second = self.d.f.new_line(quantity=QuantityVO(Decimal(10)))
        self.transfer = self.d.f.confirm(self.d.f.add(self.d.f.add(), second))
        self.bindings = self.new_bindings()
        a = self.build()
        t = self.build(StockOperationType.RECEIPT)
        self.assertEqual(len(a.lines), 2)
        self.assertEqual(
            {line.source.reference for line in a.lines},
            {line.source.reference for line in t.lines},
        )
        self.assertEqual(
            [line.source.reference for line in a.lines],
            sorted(line.source.reference for line in a.lines),
        )
        self.assertEqual(
            {line.planned_qty.value for line in a.lines}, {Decimal(50), Decimal(10)}
        )

    def test_partial_dispatch_changes_new_document_plan_to_remaining_quantity(
        self,
    ) -> None:
        """После отправки 20 из 50 новые документы планируют оставшиеся 30 без повторного пересчёта G."""
        self.transfer = self.d.register()
        plan = self.transfer.dispatch_document_snapshot()
        self.assertEqual(plan.lines[0].remaining_qty.value, Decimal(30))
        self.assertEqual(self.build().lines[0].planned_qty.value, Decimal(30))
        self.assertEqual(self.build(StockOperationType.RECEIPT).source.version, 3)

    def test_fully_dispatched_lines_are_excluded_and_no_open_plan_cannot_build(
        self,
    ) -> None:
        """Пустой остаток при ещё незавершённой приёмке не позволяет создать новые документы отправки."""
        line = replace(
            self.transfer.lines[0], dispatched_qty=self.transfer.lines[0].planned_qty
        )
        self.transfer = self.d.restore(
            self.transfer,
            status=StockTransferStatus.IN_PROGRESS,
            transit=self.d.transit,
            lines=(line,),
            version=3,
        )
        self.assertEqual(self.transfer.dispatch_document_snapshot().lines, ())
        with self.assertRaises(EmptyStockDocumentError):
            self.build(line_bindings=())
        # При наличии другой открытой строки полностью отправленная также исключается.
        other = self.d.f.new_line()
        mixed = self.d.restore(self.transfer, lines=(line, other))
        self.assertEqual(
            [row.transfer_line_id for row in mixed.dispatch_document_snapshot().lines],
            [other.id],
        )

    def test_creation_rejects_draft_cancelled_completed_or_unsupported_operation(
        self,
    ) -> None:
        """Планирование документов доступно только открытым подтверждённым перемещениям и двум ролям отправки."""
        for transfer in (self.d.f.add(), self.d.f.cancel(self.d.f.add())):
            with self.assertRaises(StockTransferStatusError):
                self.build(transfer=transfer.dispatch_document_snapshot())
        complete_line = replace(
            self.transfer.lines[0],
            dispatched_qty=self.transfer.lines[0].planned_qty,
            received_qty=self.transfer.lines[0].planned_qty,
        )
        completed = self.d.restore(
            self.transfer,
            lines=(complete_line,),
            transit=self.d.transit,
            status=StockTransferStatus.COMPLETED,
        )
        with self.assertRaises(StockTransferStatusError):
            self.build(transfer=completed.dispatch_document_snapshot())
        for operation in (StockOperationType.INTERNAL_MOVE, "ISSUE", None):
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                self.build(operation_type=operation)

    def test_creation_requires_three_current_active_warehouses_in_correct_roles(
        self,
    ) -> None:
        """Отправка требует активные A/B/T; перестановка A и B или транзит в конечный склад запрещены."""
        for name, warehouse in (
            ("source_warehouse", self.d.f.source),
            ("destination_warehouse", self.d.f.destination),
            ("transit_warehouse", self.d.transit_warehouse),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.build(**{name: replace(warehouse, is_active=False)})
        with self.assertRaises(InvalidStockDocumentContextError):
            self.build(
                source_warehouse=self.d.f.destination,
                destination_warehouse=self.d.f.source,
            )
        with self.assertRaises(StockTransferTransitMismatchError):
            self.build(transit_warehouse=self.d.f.destination)

    def test_creation_and_confirmation_use_already_fixed_transit_warehouse(
        self,
    ) -> None:
        """Новые документы после отправки не могут переназначить зафиксированный транзит."""
        self.transfer = self.d.register()
        with self.assertRaises(StockTransferTransitMismatchError):
            self.build(
                transit_warehouse=replace(
                    self.d.transit_warehouse, id=WarehouseIdVO(uuid4())
                )
            )
        self.issue, self.receipt = self.build(), self.build(StockOperationType.RECEIPT)
        wrong = replace(
            self.receipt.transfer_dispatch_snapshot(),
            warehouse_id=WarehouseIdVO(uuid4()),
        )
        with self.assertRaises(StockTransferTransitMismatchError):
            self.confirm(self.issue, companion_document=wrong)

    def test_creation_requires_exact_current_inventory_snapshots_and_base_uom(
        self,
    ) -> None:
        """Отсутствующие, лишние, повторные и неверные снимки товара не образуют новый план."""
        item = self.d.f.item.document_snapshot()
        for values in (
            (),
            (item, item),
            [item],
            (None,),
            (replace(item, inventory_item_id=InventoryItemIdVO(uuid4())),),
        ):
            with self.assertRaises(InventoryError):
                self.build(inventory_items=values)
        with self.assertRaises(StockDocumentUomMismatchError):
            self.build(inventory_items=(replace(item, base_uom=UomCodeVO("G")),))
        current = replace(item, quantity_rules=QuantityRulesVO(Decimal(3)))
        with self.assertRaises(QuantityStepError):
            self.build(inventory_items=(current,))

    def test_current_sku_is_copied_without_mutating_transfer_history(self) -> None:
        """Документы фиксируют текущий SKU, не меняя сохранённый ввод перемещения."""
        current = replace(self.d.f.item.document_snapshot(), sku=SkuVO("NEW-GRAIN"))
        self.assertEqual(
            self.build(inventory_items=(current,)).lines[0].sku, current.sku
        )
        self.assertEqual(
            self.transfer.lines[0].conversion.quantity.value, Decimal(50000)
        )

    def test_serial_and_lot_items_can_be_planned_without_selecting_instances_or_dates(
        self,
    ) -> None:
        """SERIAL планируется целыми PCS, LOT/REQUIRED не требует выбора фактической партии на стадии документа."""
        for mode, unit, expiration in (
            (TrackingMode.SERIAL, "PCS", ExpirationMode.NONE),
            (TrackingMode.LOT, "KG", ExpirationMode.REQUIRED),
        ):
            item = InventoryItem.create(
                identifier=InventoryItemIdVO(uuid4()),
                sku=SkuVO("TRACKED"),
                base_uom=UomCodeVO(unit),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
                expiration_mode=expiration,
            )
            line = self.d.f.new_line(
                inventory_item=item.stock_snapshot(),
                quantity=QuantityVO(Decimal(5)),
                uom=item.base_uom,
            )
            transfer = self.d.f.create()
            transfer = transfer.add_line(
                line,
                expected_version=0,
                inventory_item=item.stock_snapshot(),
                updated_at=self.time,
            )
            transfer = transfer.confirm(
                expected_version=1,
                source_warehouse=self.d.f.source,
                destination_warehouse=self.d.f.destination,
                inventory_items=(item.stock_snapshot(),),
                updated_at=self.time,
            )
            binding = StockTransferDispatchDocumentLineBindingVO(
                line.id, StockDocumentLineIdVO(uuid4()), StockDocumentLineIdVO(uuid4())
            )
            document = self.build(
                transfer=transfer.dispatch_document_snapshot(),
                inventory_items=(item.document_snapshot(),),
                line_bindings=(binding,),
            )
            self.assertEqual(document.lines[0].planned_qty.value, Decimal(5))
            self.assertEqual(document.lines[0].base_uom, item.base_uom)

    def test_confirm_both_sides_preserves_originals_and_transfer_progress(self) -> None:
        """Подтверждение возвращает отдельные версии 1, не фиксируя отправку или транзит."""
        issue = self.confirm(self.issue)
        receipt = self.confirm(
            self.receipt, companion_document=issue.transfer_dispatch_snapshot()
        )
        self.assertEqual(
            (issue.status, receipt.status, issue.version, receipt.version),
            (StockDocumentStatus.CONFIRMED, StockDocumentStatus.CONFIRMED, 1, 1),
        )
        self.assertEqual(self.issue.status, StockDocumentStatus.DRAFT)
        self.assertEqual((self.transfer.version, self.transfer.transit), (2, None))
        self.assertEqual(self.transfer.lines[0].dispatched_qty.value, Decimal(0))

    def test_confirmation_cannot_omit_or_replace_transfer_or_companion_context(
        self,
    ) -> None:
        """Даже вручную созданный документ с зарезервированным основанием требует весь актуальный контекст."""
        for changes in (
            dict(transfer=None),
            dict(transfer=self.transfer),
            dict(companion_document=None),
            dict(companion_document=self.receipt),
            dict(transfer_warehouses=None),
            dict(transfer_warehouses=()),
        ):
            with self.assertRaises(InventoryError):
                self.confirm(self.issue, **changes)
        with self.assertRaises(InventoryError):
            self.issue.confirm(
                warehouse=self.d.f.source,
                inventory_items=(self.d.f.item.document_snapshot(),),
                updated_at=self.time,
            )

    def test_stale_source_version_rejects_either_side_even_if_remaining_still_fits(
        self,
    ) -> None:
        """Изменение основания инвалидирует черновик; сохранённую source.version нельзя молча обновить."""
        self.transfer = self.d.register()
        for document in (self.issue, self.receipt):
            with self.assertRaises(StaleStockTransferDocumentSourceError):
                self.confirm(document)
        fresh_issue = self.build()
        with self.assertRaises(StaleStockTransferDocumentSourceError):
            self.confirm(fresh_issue)  # Сопряжённый черновик ещё ссылается на v2.

    def test_pair_rejects_other_transfer_owner_role_or_same_document_identity(
        self,
    ) -> None:
        """Парой не становятся два расхода, чужое основание/владелец или одинаковый ID документа."""
        companion = self.receipt.transfer_dispatch_snapshot()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(operation_type=StockOperationType.ISSUE),
            dict(id=self.issue.id),
        ):
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                self.confirm(
                    self.issue, companion_document=replace(companion, **changes)
                )
        with self.assertRaises(StockDocumentTransferDispatchMismatchError):
            self.confirm(
                self.issue,
                companion_document=replace(
                    companion,
                    lines=(
                        replace(
                            companion.lines[0], document_line_id=self.issue.lines[0].id
                        ),
                    ),
                ),
            )

    def test_pair_rejects_wrong_source_and_destination_warehouse(self) -> None:
        """Приход на B не заменяет приход в отдельный T, расход должен быть именно со склада A."""
        with self.assertRaises(StockTransferTransitMismatchError):
            self.confirm(
                self.issue,
                companion_document=replace(
                    self.receipt.transfer_dispatch_snapshot(),
                    warehouse_id=self.d.f.destination.id,
                ),
            )
        wrong = self.restore(self.issue, warehouse_id=self.d.f.destination.id)
        with self.assertRaises(StockDocumentTransferDispatchMismatchError):
            self.confirm(wrong, warehouse=self.d.f.destination)

    def test_pair_plans_must_match_after_draft_edits(self) -> None:
        """Изменение одного черновика запрещает подтверждение, одинаковое изменение обеих сторон допустимо."""
        issue = self.change(self.issue)
        with self.assertRaises(UnbalancedStockTransferDispatchDocumentsError):
            self.confirm(issue)
        receipt = self.change(self.receipt)
        self.assertEqual(
            self.confirm(issue, companion_document=receipt.transfer_dispatch_snapshot())
            .lines[0]
            .planned_qty.value,
            Decimal(20),
        )
        self.assertEqual(issue.lines[0].source, self.issue.lines[0].source)
        self.assertEqual(issue.lines[0].sku, self.issue.lines[0].sku)

    def test_equal_pair_cannot_exceed_current_remaining_plan(self) -> None:
        """Равные 60/60 не допускаются при открытом остатке 50."""
        issue, receipt = self.change(self.issue, "60"), self.change(self.receipt, "60")
        with self.assertRaises(StockDocumentTransferDispatchQuantityExceededError):
            self.confirm(issue, companion_document=receipt.transfer_dispatch_snapshot())

    def test_pair_cannot_reassign_to_another_line_or_change_item_or_uom(self) -> None:
        """Совпадение сторон не подменяет проверку их строк относительно основания перемещения."""
        a, t = (
            self.issue.transfer_dispatch_snapshot(),
            self.receipt.transfer_dispatch_snapshot(),
        )
        for changes in (
            dict(transfer_line_id=StockTransferLineIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                StockTransferDispatchDocumentPolicy.ensure_pair_compatible(
                    first=replace(a, lines=(replace(a.lines[0], **changes),)),
                    second=replace(t, lines=(replace(t.lines[0], **changes),)),
                    transfer=self.transfer.dispatch_document_snapshot(),
                    warehouses=(
                        self.d.f.source,
                        self.d.f.destination,
                        self.d.transit_warehouse,
                    ),
                    as_of=self.time,
                )

    def test_confirmation_rechecks_three_warehouse_activity_and_exact_context(
        self,
    ) -> None:
        """Старый черновик нельзя подтвердить после деактивации A/B/T или с неполным набором складов."""
        warehouses = (self.d.f.source, self.d.f.destination, self.d.transit_warehouse)
        for index in range(3):
            changed = tuple(
                replace(value, is_active=False) if position == index else value
                for position, value in enumerate(warehouses)
            )
            with self.assertRaises(WarehouseInactiveError):
                self.confirm(self.issue, transfer_warehouses=changed)
        for values in (
            warehouses[:2],
            warehouses + warehouses[:1],
            list(warehouses),
            (None,),
        ):
            with self.assertRaises(InventoryError):
                self.confirm(self.issue, transfer_warehouses=values)
        self.assertEqual(
            self.confirm(
                self.issue, transfer_warehouses=tuple(reversed(warehouses))
            ).status,
            StockDocumentStatus.CONFIRMED,
        )

    def test_confirm_rechecks_current_quantity_rules(self) -> None:
        """Актуальный шаг проверяется повторно перед подтверждением старого черновика."""
        item = replace(
            self.d.f.item.document_snapshot(),
            quantity_rules=QuantityRulesVO(Decimal(3)),
        )
        with self.assertRaises(QuantityStepError):
            self.confirm(self.issue, inventory_items=(item,))

    def test_companion_must_not_be_cancelled_or_already_executing(self) -> None:
        """Подтверждение пары происходит до исполнения обеих сторон; отменённый план не является основанием пары."""
        cancelled = self.receipt.cancel(updated_at=self.time)
        with self.assertRaises(StockDocumentNotDraftError):
            self.confirm(
                self.issue, companion_document=cancelled.transfer_dispatch_snapshot()
            )
        active = self.confirm(self.receipt)
        execution = self.execution(active, "20")
        partial = active.register_execution(
            execution.snapshot_for_document(), updated_at=self.time
        )
        with self.assertRaises(StockDocumentNotDraftError):
            self.confirm(
                self.issue, companion_document=partial.transfer_dispatch_snapshot()
            )

    def test_restore_preserves_historical_basis_without_fresh_context(self) -> None:
        """Restore требует только собственные инварианты; текущие склады, версия основания и второй документ не загружаются."""
        active = self.confirm(self.issue)
        self.assertEqual(self.restore(active), active)
        self.transfer = self.d.register()
        self.assertEqual(self.restore(active).source.version, 2)
        with self.assertRaises(FrozenInstanceError):
            active.source = None

    def test_restore_rejects_bad_header_role_version_or_uuid(self) -> None:
        """Зарезервированное основание проверяется и без фабрики построения документов."""
        for source in (
            replace(self.issue.source, version=None),
            replace(
                self.issue.source,
                system=StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
            ),
            replace(self.issue.source, reference="not-uuid"),
            replace(
                self.issue.source, reference="{" + self.issue.source.reference + "}"
            ),
        ):
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                self.restore(self.issue, source=source)
        with self.assertRaises(StockDocumentTransferDispatchMismatchError):
            self.restore(self.issue, operation_type=StockOperationType.INTERNAL_MOVE)

    def test_restore_rejects_orphan_missing_duplicate_or_foreign_line_sources(
        self,
    ) -> None:
        """TransferLine не существует как основание строки без правильной шапки или с повтором ссылки."""
        for source in (None, DocumentSourceVO("other", "reference")):
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                self.restore(self.issue, source=source)
        for source in (
            None,
            DocumentLineSourceVO("other", "reference"),
            DocumentLineSourceVO(
                StockTransferDispatchDocumentPolicy.LINE_SOURCE_SYSTEM, "bad-uuid"
            ),
        ):
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                self.restore(
                    self.issue, lines=(replace(self.issue.lines[0], source=source),)
                )
        duplicate = replace(self.issue.lines[0], id=StockDocumentLineIdVO(uuid4()))
        with self.assertRaises(StockDocumentTransferDispatchMismatchError):
            self.restore(self.issue, lines=(self.issue.lines[0], duplicate))

    def test_transfer_snapshot_runtime_validation_covers_types_ranges_and_states(
        self,
    ) -> None:
        """Сырой dataclass не обходит потребителя: версии, UTC, типы, нули и повтор строк проверяются явно."""
        snapshot = self.transfer.dispatch_document_snapshot()
        for changes in (
            dict(version=True),
            dict(id=uuid4()),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(lines=list(snapshot.lines)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(lines=(None,)),
            dict(
                lines=(
                    replace(snapshot.lines[0], remaining_qty=QuantityVO(Decimal(0))),
                )
            ),
            dict(status=StockTransferStatus.COMPLETED),
        ):
            with self.assertRaises(InvalidStockTransferDispatchDocumentSnapshotError):
                self.build(transfer=replace(snapshot, **changes))
        corrupted = replace(self.transfer, version=True)
        with self.assertRaises(InvalidStockTransferValueError):
            corrupted.dispatch_document_snapshot()

    def test_document_snapshot_runtime_validation_covers_source_and_progress(
        self,
    ) -> None:
        """Снимки сторон валидируют строгие версии, операции, прогресс и уникальность связей."""
        snapshot = self.receipt.transfer_dispatch_snapshot()
        for changes in (
            dict(version=True),
            dict(source_transfer_version=True),
            dict(operation_type="RECEIPT"),
            dict(operation_type=StockOperationType.INTERNAL_MOVE),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(
                lines=(replace(snapshot.lines[0], planned_qty=QuantityVO(Decimal(0))),)
            ),
        ):
            with self.assertRaises(InventoryError):
                self.confirm(
                    self.issue, companion_document=replace(snapshot, **changes)
                )

    def test_time_is_explicit_monotonic_utc_and_includes_both_document_states(
        self,
    ) -> None:
        """Фабрика и подтверждение не читают часы; будущее состояние любой стороны отклоняет раннее решение."""
        for time in (
            self.time - timedelta(seconds=1),
            self.time.replace(tzinfo=None),
            None,
        ):
            with self.assertRaises(StockDocumentTimeError):
                self.build(created_at=time)
            with self.assertRaises(StockDocumentTimeError):
                self.confirm(self.issue, updated_at=time)
        future = replace(
            self.receipt.transfer_dispatch_snapshot(),
            updated_at=self.time + timedelta(seconds=1),
        )
        with self.assertRaises(StockDocumentTimeError):
            self.confirm(self.issue, companion_document=future)
        zoned = self.time.astimezone(timezone(timedelta(hours=3)))
        self.assertEqual(
            self.build(created_at=zoned).created_at.utcoffset(), timedelta(0)
        )
        self.assertEqual(
            self.confirm(self.issue, updated_at=zoned).updated_at.utcoffset(),
            timedelta(0),
        )

    def test_ordinary_sources_still_work_and_cannot_accept_transfer_context(
        self,
    ) -> None:
        """Универсальные внешние основания сохраняют прежнее поведение; лишний контекст перемещения запрещён."""
        ordinary = self.restore(
            self.issue,
            source=DocumentSourceVO("external", "ORDER-001"),
            lines=(replace(self.issue.lines[0], source=None),),
        )
        with self.assertRaises(InvalidStockDocumentContextError):
            self.confirm(ordinary)
        confirmed = ordinary.confirm(
            warehouse=self.d.f.source,
            inventory_items=(self.d.f.item.document_snapshot(),),
            updated_at=self.time,
        )
        self.assertEqual(confirmed.status, StockDocumentStatus.CONFIRMED)
        with self.assertRaises(StockDocumentTransferDispatchMismatchError):
            ordinary.transfer_dispatch_snapshot()

    def test_hostile_decimal_context_does_not_round_remaining_or_document_quantities(
        self,
    ) -> None:
        """Вычитание 50−20 и создание базовых строк точны при внешней точности 1 с запрещённым округлением."""
        self.transfer = self.d.register()
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.issue, self.receipt = self.build(), self.build(
                StockOperationType.RECEIPT
            )
            self.assertEqual(
                self.confirm(self.issue).lines[0].planned_qty.value, Decimal(30)
            )

    def test_partial_facts_use_existing_document_transfer_and_posting_flow(
        self,
    ) -> None:
        """Планы 50 исполняются 20+30; source.version остаётся 2, текущий StockTransfer меняется v2→v3→v4."""
        issue = self.confirm(self.issue)
        receipt = self.confirm(
            self.receipt, companion_document=issue.transfer_dispatch_snapshot()
        )
        source, transit = self.d.source_position, self.d.transit_position
        for value in ("20", "30"):
            outgoing, incoming = self.execution(issue, value), self.execution(
                receipt, value
            )
            dispatch = self.d.build(
                transfer=self.transfer.dispatch_snapshot(),
                issue=outgoing.transfer_snapshot(),
                receipt=incoming.transfer_snapshot(),
                issue_bindings=self.d.bindings(outgoing),
                receipt_bindings=self.d.bindings(incoming),
            )
            issue = issue.register_execution(
                outgoing.snapshot_for_document(), updated_at=self.time
            )
            receipt = receipt.register_execution(
                incoming.snapshot_for_document(), updated_at=self.time
            )
            self.transfer = self.d.register(dispatch, self.transfer)
            out_posting = self.d.posting(outgoing, source, self.d.source_location)
            in_posting = self.d.posting(incoming, transit, self.d.transit_location)
            self.assertEqual(out_posting.posted_at, in_posting.posted_at)
            source = source.apply_posting_entry(
                out_posting.entries[0].snapshot(),
                expected_version=source.version,
                inventory_item=self.d.f.item.stock_snapshot(),
                location=self.d.source_location,
                warehouse=self.d.f.source,
            )
            transit = transit.apply_posting_entry(
                in_posting.entries[0].snapshot(),
                expected_version=transit.version,
                inventory_item=self.d.f.item.stock_snapshot(),
                location=self.d.transit_location,
                warehouse=self.d.transit_warehouse,
            )
            self.assertEqual((issue.source.version, receipt.source.version), (2, 2))
            self.assertEqual(
                issue.transfer_dispatch_snapshot().source_transfer_version, 2
            )
            self.assertEqual(
                source.on_hand_qty.value + transit.on_hand_qty.value, Decimal(50)
            )
            if value == "20":
                self.assertEqual(
                    (issue.status, receipt.status),
                    (
                        StockDocumentStatus.PARTIALLY_EXECUTED,
                        StockDocumentStatus.PARTIALLY_EXECUTED,
                    ),
                )
                self.assertEqual(
                    (
                        self.transfer.version,
                        self.transfer.lines[0].dispatched_qty.value,
                    ),
                    (3, Decimal(20)),
                )
        self.assertEqual(
            (issue.status, receipt.status),
            (StockDocumentStatus.COMPLETED, StockDocumentStatus.COMPLETED),
        )
        self.assertEqual(
            (self.transfer.status, self.transfer.version),
            (StockTransferStatus.IN_PROGRESS, 4),
        )
        self.assertEqual(
            (source.on_hand_qty.value, transit.on_hand_qty.value),
            (Decimal(0), Decimal(50)),
        )
        self.assertEqual(self.transfer.lines[0].received_qty.value, Decimal(0))
        self.assertEqual(self.issue.status, StockDocumentStatus.DRAFT)

    def test_matching_nonempty_subset_of_draft_lines_can_be_confirmed(self) -> None:
        """Удаление одной строки требует такого же изменения партнёра, сохраняя непустой план."""
        second = self.d.f.new_line(quantity=QuantityVO(Decimal(10)))
        self.transfer = self.d.f.confirm(self.d.f.add(self.d.f.add(), second))
        self.bindings = self.new_bindings()
        self.issue, self.receipt = self.build(), self.build(StockOperationType.RECEIPT)
        binding = next(
            value for value in self.bindings if value.transfer_line_id == second.id
        )
        reduced_issue = self.issue.remove_line(
            binding.issue_document_line_id, updated_at=self.time
        )
        with self.assertRaises(UnbalancedStockTransferDispatchDocumentsError):
            self.confirm(reduced_issue)
        reduced_receipt = self.receipt.remove_line(
            binding.receipt_document_line_id, updated_at=self.time
        )
        confirmed = self.confirm(
            reduced_issue,
            companion_document=reduced_receipt.transfer_dispatch_snapshot(),
        )
        self.assertEqual(len(confirmed.lines), 1)
        self.assertEqual(
            confirmed.lines[0].source.reference, str(self.d.f.line.id.uuid)
        )

    def test_equal_pair_cannot_exchange_quantities_between_same_item_obligations(
        self,
    ) -> None:
        """Равная сумма по товару не позволяет заменить планы 50/10 на 10/50 в разных TransferLine."""
        second = self.d.f.new_line(quantity=QuantityVO(Decimal(10)))
        self.transfer = self.d.f.confirm(self.d.f.add(self.d.f.add(), second))
        self.bindings = self.new_bindings()
        a, t = (
            self.build().transfer_dispatch_snapshot(),
            self.build(StockOperationType.RECEIPT).transfer_dispatch_snapshot(),
        )

        def swapped(
            snapshot: StockDocumentTransferDispatchSnapshot,
        ) -> StockDocumentTransferDispatchSnapshot:
            """Меняет количества по ID основания, не меняя общую сумму пары."""
            return replace(
                snapshot,
                lines=tuple(
                    replace(
                        line,
                        planned_qty=QuantityVO(
                            Decimal(
                                10 if line.transfer_line_id == self.d.f.line.id else 50
                            )
                        ),
                    )
                    for line in snapshot.lines
                ),
            )

        with self.assertRaises(StockDocumentTransferDispatchQuantityExceededError):
            StockTransferDispatchDocumentPolicy.ensure_pair_compatible(
                first=swapped(a),
                second=swapped(t),
                transfer=self.transfer.dispatch_document_snapshot(),
                warehouses=(
                    self.d.f.source,
                    self.d.f.destination,
                    self.d.transit_warehouse,
                ),
                as_of=self.time,
            )

    def test_pair_validation_does_not_claim_global_reservation_or_pair_deduplication(
        self,
    ) -> None:
        """Другая пара того же основания не резервирует план; физические факты ограничивает текущий StockTransfer."""
        self.bindings = self.new_bindings()
        a, t = self.build(), self.build(StockOperationType.RECEIPT)
        self.assertNotEqual((a.id, t.id), (self.issue.id, self.receipt.id))
        self.assertEqual(
            self.confirm(a, companion_document=t.transfer_dispatch_snapshot()).status,
            StockDocumentStatus.CONFIRMED,
        )
        self.assertEqual(self.transfer.lines[0].dispatched_qty.value, Decimal(0))


if __name__ == "__main__":
    unittest.main()
