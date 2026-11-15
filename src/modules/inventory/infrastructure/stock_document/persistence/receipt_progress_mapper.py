from decimal import Decimal
from src.modules.inventory.application.stock_document.query.prepare_receipt.dto import (
    PrepareReceiptLineDTO,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.dto import (
    ListReceiptExecutionLineDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)


class ReceiptProgressQueryMapper:
    """Преобразует типизированные SQL-проекции прогресса без восстановления агрегатов."""

    @staticmethod
    def to_preparation_line(
        line: StockDocumentLineModel, item: InventoryItemModel, remaining: Decimal
    ) -> PrepareReceiptLineDTO:
        """Сохраняет идентичность строки и точные серверные количества."""
        return PrepareReceiptLineDTO(
            document_line_id=line.id,
            position=line.position,
            planned_quantity=line.planned_qty,
            executed_quantity=line.executed_qty,
            inventory_item_id=item.id,
            sku=line.sku,
            base_uom=line.base_uom,
            current_base_uom=item.base_uom,
            remaining_quantity=remaining,
            quantity_step=item.quantity_step,
            tracking_mode=item.tracking_mode,
            expiration_mode=item.expiration_mode,
        )

    @staticmethod
    def to_history_line(
        line: StockDocumentLineModel, base_uom: str, quantity: Decimal, count: int
    ) -> ListReceiptExecutionLineDTO:
        """Передаёт SQL-сумму распределений только одной строки одного исполнения."""
        return ListReceiptExecutionLineDTO(
            document_line_id=line.id,
            position=line.position,
            sku=line.sku,
            base_uom=base_uom,
            quantity=quantity,
            allocation_count=count,
        )
