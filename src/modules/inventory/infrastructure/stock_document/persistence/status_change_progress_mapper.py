from src.modules.inventory.application.stock_document.query.list_status_change_sources.dto import (
    StatusChangeSourceItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)
from decimal import Decimal
from src.modules.inventory.application.stock_document.query.prepare_status_change.dto import (
    PrepareStatusChangeLineDTO,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.dto import (
    ListStatusChangeExecutionLineDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)


class StatusChangeProgressQueryMapper:
    """Преобразует типизированные SQL-проекции прогресса без восстановления агрегатов."""

    @staticmethod
    def to_preparation_line(
        line: StockDocumentLineModel, item: InventoryItemModel, remaining: Decimal
    ) -> PrepareStatusChangeLineDTO:
        """Сохраняет идентичность строки и точные серверные количества."""
        return PrepareStatusChangeLineDTO(
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
    ) -> ListStatusChangeExecutionLineDTO:
        """Передаёт SQL-сумму распределений только одной строки одного исполнения."""
        return ListStatusChangeExecutionLineDTO(
            document_line_id=line.id,
            position=line.position,
            sku=line.sku,
            base_uom=base_uom,
            quantity=quantity,
            allocation_count=count,
        )

    @staticmethod
    def to_source(
        position: StockPositionModel,
        location: StockLocationModel,
        lot: StockLotModel | None,
        serial: StockSerialModel | None,
    ) -> StatusChangeSourceItemDTO:
        """Передаёт текущую физическую позицию; даты берутся только из партии."""
        return StatusChangeSourceItemDTO(
            position.id,
            position.inventory_item_id,
            position.location_id,
            location.code,
            position.stock_status,
            position.lot_id,
            lot.number if lot else None,
            position.serial_id,
            serial.number if serial else None,
            lot.manufactured_on if lot else None,
            lot.expires_on if lot else None,
            position.base_uom,
            position.on_hand_qty,
            position.version,
        )
