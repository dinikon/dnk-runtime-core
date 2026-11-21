from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_document import (
    StockExecutionDocumentPolicy,
)
from src.modules.inventory.domain.stock_document.execution_snapshot import (
    StockDocumentExecutionSnapshot,
    StockDocumentLineExecutionSnapshot,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentContextError,
)
from src.modules.inventory.domain.stock_document.transfer_dispatch_snapshot import (
    StockDocumentTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_document.transfer_receipt_snapshot import (
    StockDocumentTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.document_snapshot import (
    StockExecutionDocumentSnapshot,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferDocumentSnapshotError,
)
from src.modules.inventory.domain.stock_execution.transfer_document_snapshot import (
    StockExecutionTransferDocumentSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.document_line_quantity import (
    ExecutedDocumentLineQuantityVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockTransferDocumentExecutionPolicy:
    """Проверяет документные связи и лимиты фактов обоих этапов, не подменяя правила самого перемещения."""

    @staticmethod
    def build_bindings(
        *,
        document: (
            StockDocumentTransferDispatchSnapshot | StockDocumentTransferReceiptSnapshot
        ),
        execution: StockExecutionTransferDocumentSnapshot,
    ) -> tuple[StockTransferExecutionBindingVO, ...]:
        """Назначает все целые фактические строки и проверяет точные суммы относительно версии и остатка своего документа."""
        if not isinstance(
            document,
            (
                StockDocumentTransferDispatchSnapshot,
                StockDocumentTransferReceiptSnapshot,
            ),
        ):
            raise InvalidStockDocumentContextError(
                "Нужен снимок документа одного из этапов StockTransfer."
            )
        document.ensure_valid()
        if not isinstance(execution, StockExecutionTransferDocumentSnapshot):
            raise InvalidStockExecutionTransferDocumentSnapshotError(
                "Нужен снимок факта с документными связями."
            )
        execution.ensure_valid()
        by_line = {line.document_line_id: line for line in document.lines}
        quantities: dict[StockDocumentLineIdVO, QuantityVO] = {}
        bindings = []
        for actual in sorted(
            execution.lines, key=lambda line: line.execution_line_id.uuid.int
        ):
            planned = by_line.get(actual.document_line_id)
            if (
                planned is None
                or planned.inventory_item_id != actual.inventory_item_id
                or planned.base_uom != actual.base_uom
            ):
                raise InvalidStockDocumentContextError(
                    "Каждый факт должен соответствовать строке, товару и единице своего документа."
                )
            previous = quantities.get(actual.document_line_id)
            quantities[actual.document_line_id] = (
                actual.quantity
                if previous is None
                else QuantityArithmeticPolicy.add(previous, actual.quantity)
            )
            bindings.append(
                StockTransferExecutionBindingVO(
                    actual.execution_line_id, planned.transfer_line_id
                )
            )
        StockExecutionDocumentPolicy.ensure_compatible(
            document=StockDocumentExecutionSnapshot(
                document.id,
                document.operation_type,
                document.warehouse_id,
                document.owner_id,
                document.status,
                document.version,
                document.updated_at,
                tuple(
                    StockDocumentLineExecutionSnapshot(
                        line.document_line_id,
                        line.inventory_item_id,
                        line.base_uom,
                        line.planned_qty,
                        line.executed_qty,
                    )
                    for line in document.lines
                ),
            ),
            execution=StockExecutionDocumentSnapshot(
                execution.id,
                execution.document_id,
                execution.document_version,
                execution.operation_type,
                execution.warehouse_id,
                execution.owner_id,
                execution.executed_at,
                tuple(
                    ExecutedDocumentLineQuantityVO(
                        identifier,
                        by_line[identifier].inventory_item_id,
                        by_line[identifier].base_uom,
                        quantities[identifier],
                    )
                    for identifier in sorted(
                        quantities, key=lambda value: value.uuid.int
                    )
                ),
            ),
        )
        return tuple(bindings)
