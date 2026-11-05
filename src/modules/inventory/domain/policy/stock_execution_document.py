from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentContextError,
    InvalidStockDocumentExecutionSnapshotError,
    StaleStockDocumentVersionError,
    StockDocumentExecutionNotAllowedError,
    StockDocumentOverExecutionError,
)
from src.modules.inventory.domain.stock_document.execution_snapshot import (
    StockDocumentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.document_snapshot import (
    StockExecutionDocumentSnapshot,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionDocumentSnapshotError,
    StockExecutionTimeError,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)


class StockExecutionDocumentPolicy:
    """Проверяет исполнение относительно текущего плана и накопленного прогресса каждой строки."""

    @staticmethod
    def ensure_compatible(
        *,
        document: StockDocumentExecutionSnapshot,
        execution: StockExecutionDocumentSnapshot,
    ) -> None:
        """Требует исполняемый план той же версии и запрещает превышение по каждой строке."""
        if not isinstance(document, StockDocumentExecutionSnapshot):
            raise InvalidStockDocumentExecutionSnapshotError(
                "Нужен снимок плана для исполнения."
            )
        if not isinstance(execution, StockExecutionDocumentSnapshot):
            raise InvalidStockExecutionDocumentSnapshotError(
                "Нужен снимок фактического исполнения."
            )
        if document.operation_type is StockOperationType.ADJUSTMENT:
            raise StockDocumentExecutionNotAllowedError(
                "Для ADJUSTMENT нужны специализированные снимки и регистрация полного исполнения."
            )
        document.ensure_valid()
        execution.ensure_valid()
        if document.status not in (
            StockDocumentStatus.CONFIRMED,
            StockDocumentStatus.PARTIALLY_EXECUTED,
        ):
            raise StockDocumentExecutionNotAllowedError(
                "Исполнение доступно только подтверждённому или частично исполненному документу."
            )
        if (
            execution.document_id != document.id
            or execution.operation_type != document.operation_type
            or execution.warehouse_id != document.warehouse_id
            or execution.owner_id != document.owner_id
        ):
            raise InvalidStockDocumentContextError(
                "Исполнение должно соответствовать документу, операции, складу и владельцу."
            )
        if execution.document_version != document.version:
            raise StaleStockDocumentVersionError(
                "Исполнение подготовлено по другой версии документа."
            )
        if execution.executed_at < document.updated_at:
            raise StockExecutionTimeError(
                "Время исполнения не может быть раньше текущей версии плана."
            )
        by_id = {line.id: line for line in document.lines}
        for actual in execution.lines:
            planned = by_id.get(actual.document_line_id)
            if (
                planned is None
                or actual.inventory_item_id != planned.inventory_item_id
                or actual.base_uom != planned.base_uom
            ):
                raise InvalidStockDocumentContextError(
                    "Фактическая строка должна соответствовать плановой строке, товару и единице."
                )
            if actual.quantity.value > planned.remaining_qty.value:
                raise StockDocumentOverExecutionError(
                    "Исполнение превышает оставшееся количество конкретной строки."
                )
