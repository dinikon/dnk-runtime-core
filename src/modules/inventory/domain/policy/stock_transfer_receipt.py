from src.modules.inventory.domain.policy.stock_transfer_document_execution import (
    StockTransferDocumentExecutionPolicy,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentTransferReceiptSnapshotError,
    StockDocumentExecutionNotAllowedError,
)
from src.modules.inventory.domain.stock_document.transfer_receipt_snapshot import (
    StockDocumentTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.transfer_document_snapshot import (
    StockExecutionTransferDocumentSnapshot,
)
from src.modules.inventory.domain.policy.stock_transfer_execution_grouping import (
    StockTransferExecutionGroupingPolicy,
)
from src.modules.inventory.domain.policy.location_availability import (
    LocationAvailabilityPolicy,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_transit_balance import (
    StockTransferTransitBalancePolicy,
)
from src.modules.inventory.domain.stock_transfer.transit_balance_snapshot import (
    StockTransferTransitBalanceSnapshot,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferSnapshotError,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.receipt_plan_snapshot import (
    StockTransferReceiptPlanSnapshot,
)
from src.modules.inventory.domain.stock_transfer.receipt_snapshot import (
    StockTransferReceivedLineSnapshot,
    StockTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferReceiptPlanSnapshotError,
    InvalidStockTransferReceiptSnapshotError,
    StockTransferReceiptMismatchError,
    StockTransferReceiptQuantityExceededError,
    StockTransferStatusError,
    StockTransferTransitStockExceededError,
    StockTransferTimeError,
    StockTransferTransitMismatchError,
    StockTransferVersionConflictError,
    UnbalancedStockTransferReceiptError,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class StockTransferReceiptPolicy:
    """Согласует расход из транзита и приход на конечный склад без изменения запасов или других корней."""

    @staticmethod
    def build_receipt_from_documents(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        balance: StockTransferTransitBalanceSnapshot,
        issue_document: StockDocumentTransferReceiptSnapshot,
        receipt_document: StockDocumentTransferReceiptSnapshot,
        issue: StockExecutionTransferDocumentSnapshot,
        receipt: StockExecutionTransferDocumentSnapshot,
        transit_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
    ) -> StockTransferReceiptSnapshot:
        """Выводит все назначения T → B из оснований документов и проверяет документные лимиты и актуальный состав транзита."""
        if not isinstance(transfer, StockTransferReceiptPlanSnapshot):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Нужен полный текущий снимок плана приёмки StockTransfer."
            )
        transfer.ensure_valid()
        if transfer.status is not StockTransferStatus.IN_PROGRESS:
            raise StockTransferStatusError(
                "Автоматическая приёмка доступна только исполняемому перемещению."
            )
        StockTransferTransitBalancePolicy.ensure_compatible(
            transfer=transfer, balance=balance
        )
        plan = {line.id: line for line in transfer.lines}
        for document in (issue_document, receipt_document):
            if not isinstance(document, StockDocumentTransferReceiptSnapshot):
                raise InvalidStockDocumentTransferReceiptSnapshotError(
                    "Нужны снимки оснований обоих документов приёмки."
                )
            document.ensure_valid()
            if document.status not in (
                StockDocumentStatus.CONFIRMED,
                StockDocumentStatus.PARTIALLY_EXECUTED,
            ):
                raise StockDocumentExecutionNotAllowedError(
                    "Приёмка требует подтверждённые или частично исполненные документы."
                )
            if (
                document.transfer_id != transfer.id
                or document.owner_id != transfer.owner_id
            ):
                raise StockTransferReceiptMismatchError(
                    "Основание и владелец каждого документа должны соответствовать перемещению."
                )
            for row in document.lines:
                target = plan.get(row.transfer_line_id)
                if (
                    target is None
                    or target.inventory_item_id != row.inventory_item_id
                    or target.base_uom != row.base_uom
                ):
                    raise StockTransferReceiptMismatchError(
                        "Все строки документа должны соответствовать строкам, товарам и единицам текущего перемещения."
                    )
        if (
            issue_document.id == receipt_document.id
            or issue_document.operation_type is not StockOperationType.ISSUE
            or receipt_document.operation_type is not StockOperationType.RECEIPT
        ):
            raise StockTransferReceiptMismatchError(
                "Нужны разные документы расхода T и прихода B в соответствующих ролях."
            )
        if (
            issue_document.source_transfer_version
            != receipt_document.source_transfer_version
            or issue_document.source_transfer_version > transfer.version
        ):
            raise StockTransferVersionConflictError(
                "Исторические версии основания обеих сторон должны совпадать и не превышать текущую версию StockTransfer."
            )
        if {line.document_line_id for line in issue_document.lines}.intersection(
            line.document_line_id for line in receipt_document.lines
        ):
            raise StockTransferReceiptMismatchError(
                "Плановые ID строк обеих сторон должны различаться."
            )
        outgoing = {
            row.transfer_line_id: (
                row.inventory_item_id,
                row.base_uom,
                row.planned_qty,
                row.executed_qty,
            )
            for row in issue_document.lines
        }
        incoming = {
            row.transfer_line_id: (
                row.inventory_item_id,
                row.base_uom,
                row.planned_qty,
                row.executed_qty,
            )
            for row in receipt_document.lines
        }
        if outgoing != incoming:
            raise StockTransferReceiptMismatchError(
                "Планы и накопленное исполнение пары должны совпадать по каждой строке перемещения."
            )
        issue_bindings = StockTransferDocumentExecutionPolicy.build_bindings(
            document=issue_document, execution=issue
        )
        receipt_bindings = StockTransferDocumentExecutionPolicy.build_bindings(
            document=receipt_document, execution=receipt
        )
        return StockTransferReceiptPolicy.build_receipt(
            transfer=transfer,
            balance=balance,
            issue=issue.transfer_snapshot(),
            receipt=receipt.transfer_snapshot(),
            destination_warehouse=destination_warehouse,
            transit_warehouse=transit_warehouse,
            locations=locations,
            issue_bindings=issue_bindings,
            receipt_bindings=receipt_bindings,
        )

    @staticmethod
    def build_receipt(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        issue: StockExecutionTransferSnapshot,
        receipt: StockExecutionTransferSnapshot,
        balance: StockTransferTransitBalanceSnapshot,
        destination_warehouse: WarehouseSnapshot,
        transit_warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
        issue_bindings: tuple[StockTransferExecutionBindingVO, ...],
        receipt_bindings: tuple[StockTransferExecutionBindingVO, ...],
    ) -> StockTransferReceiptSnapshot:
        """Проверяет всю пару, точно балансирует сохраняемые измерения и строит одну регистрацию по версии плана."""
        if not isinstance(transfer, StockTransferReceiptPlanSnapshot):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Нужен текущий снимок плана приёмки."
            )
        transfer.ensure_valid()
        if transfer.status is not StockTransferStatus.IN_PROGRESS:
            raise StockTransferStatusError(
                "Приёмка доступна только исполняемому перемещению."
            )
        for execution in (issue, receipt):
            if not isinstance(execution, StockExecutionTransferSnapshot):
                raise InvalidStockExecutionTransferSnapshotError(
                    "Нужны специализированные снимки расхода и прихода."
                )
            execution.ensure_valid()
        StockTransferTransitBalancePolicy.ensure_compatible(
            transfer=transfer, balance=balance
        )
        transit = transfer.transit
        for warehouse, identifier in (
            (transit_warehouse, transit.warehouse_id),
            (destination_warehouse, transfer.destination_warehouse_id),
        ):
            if not isinstance(warehouse, WarehouseSnapshot):
                raise InvalidWarehouseSnapshotError(
                    "Нужен снимок транзитного или конечного склада."
                )
            warehouse.ensure_valid()
            if warehouse.id != identifier:
                raise StockTransferReceiptMismatchError(
                    "Снимок склада не соответствует маршруту приёмки."
                )
        if (
            issue.operation_type is not StockOperationType.ISSUE
            or receipt.operation_type is not StockOperationType.RECEIPT
            or issue.id == receipt.id
            or issue.warehouse_id != transit.warehouse_id
            or receipt.warehouse_id != transfer.destination_warehouse_id
            or issue.owner_id != transfer.owner_id
            or receipt.owner_id != transfer.owner_id
            or {line.id for line in issue.lines}.intersection(
                line.id for line in receipt.lines
            )
        ):
            raise StockTransferReceiptMismatchError(
                "Нужны разные ISSUE из транзита и RECEIPT на конечный склад одного владельца с разными фактическими ID."
            )
        if {issue.id, receipt.id}.intersection(balance.execution_ids) or {
            line.id for execution in (issue, receipt) for line in execution.lines
        }.intersection(balance.execution_line_ids):
            raise StockTransferReceiptMismatchError(
                "Исполнения и строки уже участвовали в истории этого перемещения."
            )
        if issue.executed_at != receipt.executed_at:
            raise StockTransferTimeError(
                "Расход из транзита и приход на конечный склад должны иметь одно время приёмки."
            )
        if not isinstance(locations, tuple):
            raise InvalidStockLocationSnapshotError(
                "Нужен tuple снимков фактических локаций пары."
            )
        by_location = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockLocationSnapshotError(
                    "Нужны снимки локаций пары приёмки."
                )
            location.ensure_valid()
            if location.id in by_location:
                raise StockTransferReceiptMismatchError(
                    "Снимки локаций не должны повторяться."
                )
            by_location[location.id] = location
        if set(by_location) != {
            line.dimensions.location_id
            for execution in (issue, receipt)
            for line in execution.lines
        }:
            raise StockTransferReceiptMismatchError(
                "Нужны ровно участвующие снимки локаций без пропусков и лишних."
            )
        for line in issue.lines:
            location = by_location[line.dimensions.location_id]
            if (
                location.id != transit.location_id
                or location.location_type is not LocationType.TRANSIT
            ):
                raise StockTransferTransitMismatchError(
                    "Весь расход должен исходить из зафиксированной локации TRANSIT."
                )
            LocationAvailabilityPolicy.ensure_available(
                location=location, warehouse=transit_warehouse
            )
        for line in receipt.lines:
            LocationAvailabilityPolicy.ensure_available(
                location=by_location[line.dimensions.location_id],
                warehouse=destination_warehouse,
            )
        plan = {line.id: line for line in transfer.lines}
        outgoing, quantities, issue_ids = StockTransferExecutionGroupingPolicy.group(
            issue, issue_bindings, plan, StockTransferReceiptMismatchError
        )
        incoming, _, receipt_ids = StockTransferExecutionGroupingPolicy.group(
            receipt, receipt_bindings, plan, StockTransferReceiptMismatchError
        )
        if outgoing != incoming:
            raise UnbalancedStockTransferReceiptError(
                "Расход и приход должны совпадать по строке, товару, владельцу, LOT/SERIAL, состоянию и единице."
            )
        available = {
            (row.transfer_line_id, row.dimensions, row.base_uom): row.quantity
            for row in balance.lines
        }
        requested = {}
        assigned = {
            binding.execution_line_id: binding.transfer_line_id
            for binding in issue_bindings
        }
        for line in issue.lines:
            key = (assigned[line.id], line.dimensions, line.base_uom)
            requested[key] = (
                line.quantity
                if key not in requested
                else QuantityArithmeticPolicy.add(requested[key], line.quantity)
            )
        for key, quantity in requested.items():
            if key not in available or quantity.value > available[key].value:
                raise StockTransferTransitStockExceededError(
                    "Недостаточно транзитного остатка конкретной строки, LOT/SERIAL и состояния."
                )
        receipt_result = StockTransferReceiptSnapshot(
            transfer.id,
            transfer.version,
            transfer.source_warehouse_id,
            transfer.destination_warehouse_id,
            transfer.owner_id,
            transit,
            issue.id,
            receipt.id,
            issue.executed_at,
            tuple(
                StockTransferReceivedLineSnapshot(
                    identifier,
                    plan[identifier].inventory_item_id,
                    plan[identifier].base_uom,
                    quantities[identifier],
                    issue_ids[identifier],
                    receipt_ids[identifier],
                )
                for identifier in sorted(quantities, key=lambda value: value.uuid.int)
            ),
        )
        StockTransferReceiptPolicy.ensure_compatible(
            transfer=transfer, receipt_result=receipt_result
        )
        return receipt_result

    @staticmethod
    def ensure_compatible(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        receipt_result: StockTransferReceiptSnapshot,
    ) -> None:
        """Повторно проверяет цель, версию, состояние, фиксированный транзит, хронологию и предел приёмки."""
        if not isinstance(transfer, StockTransferReceiptPlanSnapshot):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Нужен снимок текущего плана приёмки."
            )
        transfer.ensure_valid()
        if not isinstance(receipt_result, StockTransferReceiptSnapshot):
            raise InvalidStockTransferReceiptSnapshotError(
                "Нужен результат согласованной приёмки."
            )
        receipt_result.ensure_valid()
        if transfer.status is not StockTransferStatus.IN_PROGRESS:
            raise StockTransferStatusError(
                "Регистрировать приёмку можно только у исполняемого перемещения."
            )
        if receipt_result.transfer_version != transfer.version:
            raise StockTransferVersionConflictError(
                "Приёмка построена по другой версии StockTransfer."
            )
        if (
            receipt_result.transfer_id != transfer.id
            or receipt_result.source_warehouse_id != transfer.source_warehouse_id
            or receipt_result.destination_warehouse_id
            != transfer.destination_warehouse_id
            or receipt_result.owner_id != transfer.owner_id
        ):
            raise StockTransferReceiptMismatchError(
                "Приёмка относится к другому перемещению, направлению или владельцу."
            )
        if transfer.transit is not None and transfer.transit != receipt_result.transit:
            raise StockTransferTransitMismatchError(
                "Маршрут уже зафиксирован первой отправкой."
            )
        if receipt_result.executed_at < transfer.updated_at:
            raise StockTransferTimeError(
                "Приёмка не может предшествовать текущему состоянию перемещения."
            )
        by_line = {line.id: line for line in transfer.lines}
        for line in receipt_result.lines:
            planned = by_line.get(line.transfer_line_id)
            if (
                planned is None
                or line.inventory_item_id != planned.inventory_item_id
                or line.base_uom != planned.base_uom
            ):
                raise StockTransferReceiptMismatchError(
                    "Строка, товар и единица приёмки не соответствуют плану."
                )
            if (
                QuantityArithmeticPolicy.add(planned.received_qty, line.quantity).value
                > planned.dispatched_qty.value
            ):
                raise StockTransferReceiptQuantityExceededError(
                    "Приёмка превышает непринятое отправленное количество строки."
                )
