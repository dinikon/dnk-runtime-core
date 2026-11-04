from datetime import datetime, timedelta
from typing import ClassVar

from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_document_confirmation import (
    StockDocumentConfirmationPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_document_source import (
    StockTransferDocumentSourcePolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_transit_balance import (
    StockTransferTransitBalancePolicy,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentContextError,
    StockDocumentNotDraftError,
    InvalidStockDocumentTransferReceiptSnapshotError,
    InvalidStockTransferReceiptDocumentLineBindingError,
    StockDocumentTransferReceiptMismatchError,
    StockDocumentTransferReceiptQuantityExceededError,
    UnbalancedStockTransferReceiptDocumentsError,
    StaleStockTransferDocumentSourceError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
)
from src.modules.inventory.domain.stock_document.transfer_receipt_snapshot import (
    StockDocumentTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_document.value_object.transfer_receipt_line_binding import (
    StockTransferReceiptDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferReceiptPlanSnapshotError,
    StockTransferStatusError,
)
from src.modules.inventory.domain.stock_transfer.receipt_plan_snapshot import (
    StockTransferReceiptPlanSnapshot,
)
from src.modules.inventory.domain.stock_transfer.transit_balance_snapshot import (
    StockTransferTransitBalanceSnapshot,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class StockTransferReceiptDocumentPolicy:
    """Строит планы T → B и повторно проверяет основание и текущий непринятый транзит перед подтверждением."""

    ISSUE_SOURCE_SYSTEM: ClassVar[str] = (
        StockTransferDocumentSourcePolicy.RECEIPT_ISSUE_SYSTEM
    )
    RECEIPT_SOURCE_SYSTEM: ClassVar[str] = (
        StockTransferDocumentSourcePolicy.RECEIPT_RECEIPT_SYSTEM
    )
    LINE_SOURCE_SYSTEM: ClassVar[str] = (
        StockTransferDocumentSourcePolicy.LINE_SOURCE_SYSTEM
    )

    @staticmethod
    def source_system(operation_type: StockOperationType) -> str:
        """Выбирает отдельную роль этапа приёмки только для ISSUE T или RECEIPT B."""
        if operation_type is StockOperationType.ISSUE:
            return StockTransferReceiptDocumentPolicy.ISSUE_SOURCE_SYSTEM
        if operation_type is StockOperationType.RECEIPT:
            return StockTransferReceiptDocumentPolicy.RECEIPT_SOURCE_SYSTEM
        raise StockDocumentTransferReceiptMismatchError(
            "Документы приёмки поддерживают только ISSUE и RECEIPT."
        )

    @staticmethod
    def build_lines(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        balance: StockTransferTransitBalanceSnapshot,
        operation_type: StockOperationType,
        transit_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        line_bindings: tuple[StockTransferReceiptDocumentLineBindingVO, ...],
        as_of: datetime,
    ) -> tuple[StockDocumentLine, ...]:
        """Строит одну сторону на весь отправленный, но не принятый остаток без выбора конкретных партий или серий."""
        StockTransferReceiptDocumentPolicy.source_system(operation_type)
        StockTransferReceiptDocumentPolicy._ensure_receipt(transfer, balance, as_of)
        for warehouse, identifier in (
            (transit_warehouse, transfer.transit.warehouse_id),
            (destination_warehouse, transfer.destination_warehouse_id),
        ):
            StockDocumentConfirmationPolicy.ensure_warehouse(
                warehouse_id=identifier, warehouse=warehouse
            )
        rows = tuple(
            line for line in transfer.lines if line.dispatched_qty != line.received_qty
        )
        if not isinstance(inventory_items, tuple):
            raise InvalidStockDocumentContextError(
                "Нужен tuple текущих товарных снимков приёмки."
            )
        items = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemDocumentSnapshot):
                raise InvalidInventoryItemDocumentSnapshotError(
                    "Нужны товарные снимки документа приёмки."
                )
            item.ensure_valid()
            if item.inventory_item_id in items:
                raise InvalidStockDocumentContextError(
                    "Товарные снимки не должны повторяться."
                )
            items[item.inventory_item_id] = item
        if set(items) != {line.inventory_item_id for line in rows}:
            raise InvalidStockDocumentContextError(
                "Нужны ровно товары положительного остатка в транзите."
            )
        if not isinstance(line_bindings, tuple):
            raise InvalidStockTransferReceiptDocumentLineBindingError(
                "Назначения ID приёмочных строк передаются в tuple."
            )
        bindings, ids = {}, set()
        for binding in line_bindings:
            if not isinstance(binding, StockTransferReceiptDocumentLineBindingVO):
                raise InvalidStockTransferReceiptDocumentLineBindingError(
                    "Нужны типизированные назначения ID обеих сторон приёмки."
                )
            values = (binding.issue_document_line_id, binding.receipt_document_line_id)
            if binding.transfer_line_id in bindings or ids.intersection(values):
                raise InvalidStockTransferReceiptDocumentLineBindingError(
                    "ID оснований и всех новых строк приёмки должны быть уникальны."
                )
            bindings[binding.transfer_line_id] = binding
            ids.update(values)
        if set(bindings) != {line.id for line in rows}:
            raise InvalidStockTransferReceiptDocumentLineBindingError(
                "Нужно назначить ровно все строки с положительным остатком в транзите."
            )
        result = []
        for line in sorted(rows, key=lambda row: row.id.uuid.int):
            item = items[line.inventory_item_id]
            if item.base_uom != line.base_uom:
                raise StockDocumentUomMismatchError(
                    "Текущая базовая единица товара отличается от единицы отправки."
                )
            binding = bindings[line.id]
            result.append(
                StockDocumentLine.create(
                    identifier=(
                        binding.issue_document_line_id
                        if operation_type is StockOperationType.ISSUE
                        else binding.receipt_document_line_id
                    ),
                    inventory_item=item,
                    quantity=QuantityArithmeticPolicy.subtract(
                        line.dispatched_qty, line.received_qty
                    ),
                    uom=line.base_uom,
                    source=DocumentLineSourceVO(
                        StockTransferReceiptDocumentPolicy.LINE_SOURCE_SYSTEM,
                        str(line.id.uuid),
                    ),
                )
            )
        return tuple(result)

    @staticmethod
    def ensure_confirmable(
        *,
        document: StockDocumentTransferReceiptSnapshot | None,
        companion: StockDocumentTransferReceiptSnapshot | None,
        transfer: StockTransferReceiptPlanSnapshot | None,
        balance: StockTransferTransitBalanceSnapshot | None,
        warehouses: tuple[WarehouseSnapshot, ...] | None,
        as_of: datetime,
    ) -> None:
        """Требует весь актуальный контекст только у документов этапа приёмки и повторно согласует пару."""
        if document is None:
            if (
                companion is not None
                or transfer is not None
                or balance is not None
                or warehouses is not None
            ):
                raise InvalidStockDocumentContextError(
                    "Контекст приёмки передаётся только документам T → B."
                )
            return
        if not isinstance(document, StockDocumentTransferReceiptSnapshot):
            raise InvalidStockDocumentTransferReceiptSnapshotError(
                "Нужен снимок подтверждаемого документа приёмки."
            )
        document.ensure_valid()
        if document.status is not StockDocumentStatus.DRAFT:
            raise StockDocumentNotDraftError(
                "Подтверждать можно только черновик приёмки."
            )
        StockTransferReceiptDocumentPolicy.ensure_pair_compatible(
            first=document,
            second=companion,
            transfer=transfer,
            balance=balance,
            warehouses=warehouses,
            as_of=as_of,
        )

    @staticmethod
    def ensure_pair_compatible(
        *,
        first: StockDocumentTransferReceiptSnapshot,
        second: StockDocumentTransferReceiptSnapshot,
        transfer: StockTransferReceiptPlanSnapshot,
        balance: StockTransferTransitBalanceSnapshot,
        warehouses: tuple[WarehouseSnapshot, ...],
        as_of: datetime,
    ) -> None:
        """Проверяет актуальность основания/баланса, роли T/B и одинаковый непустой план в пределах непринятой отправки."""
        StockTransferReceiptDocumentPolicy._ensure_receipt(transfer, balance, as_of)
        for document in (first, second):
            if not isinstance(document, StockDocumentTransferReceiptSnapshot):
                raise InvalidStockDocumentTransferReceiptSnapshotError(
                    "Нужны снимки обоих документов этапа приёмки."
                )
            document.ensure_valid()
            if document.status not in (
                StockDocumentStatus.DRAFT,
                StockDocumentStatus.CONFIRMED,
            ):
                raise StockDocumentNotDraftError(
                    "Сопряжённый документ должен быть черновиком или подтверждённым планом без исполнения."
                )
            if (
                document.transfer_id != transfer.id
                or document.owner_id != transfer.owner_id
            ):
                raise StockDocumentTransferReceiptMismatchError(
                    "Основание и владелец пары должны соответствовать StockTransfer."
                )
            if document.source_transfer_version != transfer.version:
                raise StaleStockTransferDocumentSourceError(
                    "Основание изменилось: перестройте черновики приёмки по текущей версии."
                )
            if document.updated_at > as_of:
                raise StockDocumentTimeError(
                    "Подтверждение не может предшествовать состоянию любой стороны пары."
                )
        if first.id == second.id or {first.operation_type, second.operation_type} != {
            StockOperationType.ISSUE,
            StockOperationType.RECEIPT,
        }:
            raise StockDocumentTransferReceiptMismatchError(
                "Нужны два разных документа ISSUE T и RECEIPT B."
            )
        issue, receipt = (
            (first, second)
            if first.operation_type is StockOperationType.ISSUE
            else (second, first)
        )
        if (
            issue.warehouse_id != transfer.transit.warehouse_id
            or receipt.warehouse_id != transfer.destination_warehouse_id
        ):
            raise StockDocumentTransferReceiptMismatchError(
                "Склады пары должны совпадать с фиксированным T и конечным B."
            )
        StockTransferReceiptDocumentPolicy._ensure_warehouses(
            transfer=transfer, warehouses=warehouses
        )
        if {line.document_line_id for line in issue.lines}.intersection(
            line.document_line_id for line in receipt.lines
        ):
            raise StockDocumentTransferReceiptMismatchError(
                "ID плановых строк обеих сторон приёмки должны различаться."
            )
        outgoing = {
            line.transfer_line_id: (
                line.inventory_item_id,
                line.base_uom,
                line.planned_qty,
            )
            for line in issue.lines
        }
        incoming = {
            line.transfer_line_id: (
                line.inventory_item_id,
                line.base_uom,
                line.planned_qty,
            )
            for line in receipt.lines
        }
        if not outgoing or outgoing != incoming:
            raise UnbalancedStockTransferReceiptDocumentsError(
                "Планы расхода T и прихода B должны совпадать по каждой TransferLine."
            )
        plan = {line.id: line for line in transfer.lines}
        for identifier, (item_id, base_uom, quantity) in outgoing.items():
            target = plan.get(identifier)
            if (
                target is None
                or target.inventory_item_id != item_id
                or target.base_uom != base_uom
            ):
                raise StockDocumentTransferReceiptMismatchError(
                    "Строка, товар и единица пары не соответствуют перемещению."
                )
            remaining = QuantityArithmeticPolicy.subtract(
                target.dispatched_qty, target.received_qty
            )
            if quantity.value > remaining.value:
                raise StockDocumentTransferReceiptQuantityExceededError(
                    "План приёмки превышает отправленный, но ещё не принятый остаток строки."
                )

    @staticmethod
    def _ensure_receipt(
        transfer: StockTransferReceiptPlanSnapshot,
        balance: StockTransferTransitBalanceSnapshot,
        as_of: datetime,
    ) -> None:
        """Проверяет текущую версию, фиксированный транзит, согласованный баланс и наличие количества к приёмке."""
        if not isinstance(transfer, StockTransferReceiptPlanSnapshot):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Нужен текущий снимок плана приёмки StockTransfer."
            )
        transfer.ensure_valid()
        if transfer.status is not StockTransferStatus.IN_PROGRESS:
            raise StockTransferStatusError(
                "Документы приёмки доступны только исполняемому перемещению с транзитом."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < transfer.updated_at
        ):
            raise StockDocumentTimeError(
                "Нужен UTC-момент не раньше текущего состояния перемещения."
            )
        StockTransferTransitBalancePolicy.ensure_compatible(
            transfer=transfer, balance=balance
        )
        if not any(line.dispatched_qty != line.received_qty for line in transfer.lines):
            raise EmptyStockDocumentError(
                "В транзите нет отправленного, но ещё не принятого количества."
            )

    @staticmethod
    def _ensure_warehouses(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        warehouses: tuple[WarehouseSnapshot, ...],
    ) -> None:
        """Требует ровно активные T/B; исходный A после отправки не участвует в решении о приёмке."""
        if not isinstance(warehouses, tuple):
            raise InvalidWarehouseSnapshotError("Нужен tuple актуальных T и B.")
        ids = set()
        for warehouse in warehouses:
            if not isinstance(warehouse, WarehouseSnapshot):
                raise InvalidWarehouseSnapshotError(
                    "Нужны WarehouseSnapshot транзитного и конечного складов."
                )
            StockDocumentConfirmationPolicy.ensure_warehouse(
                warehouse_id=warehouse.id, warehouse=warehouse
            )
            if warehouse.id in ids:
                raise InvalidStockDocumentContextError(
                    "Снимки складов T/B не должны повторяться."
                )
            ids.add(warehouse.id)
        if ids != {transfer.transit.warehouse_id, transfer.destination_warehouse_id}:
            raise InvalidStockDocumentContextError(
                "Нужны ровно актуальные снимки зафиксированного T и конечного B."
            )
