from src.modules.inventory.application.stock_document.query.list_return_destinations.dto import (
    ReturnDestinationDTO,
)
from uuid import UUID
from src.modules.inventory.application.stock_document.query.list_return_sources.dto import (
    ReturnSourceItemDTO,
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
from src.modules.inventory.application.stock_document.query.prepare_return.dto import (
    PrepareReturnLineDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.dto import (
    ListReturnExecutionLineDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)


class ReturnProgressQueryMapper:
    """Преобразует типизированные SQL-проекции прогресса без восстановления агрегатов."""

    @staticmethod
    def to_preparation_line(
        line: StockDocumentLineModel,
        item: InventoryItemModel,
        remaining: Decimal,
        *,
        origin_line_id: UUID,
        original_quantity: Decimal,
        returned_quantity: Decimal,
        returnable_quantity: Decimal,
    ) -> PrepareReturnLineDTO:
        """Сохраняет идентичность строки и точные серверные количества."""
        return PrepareReturnLineDTO(
            document_line_id=line.id,
            origin_execution_line_id=origin_line_id,
            original_quantity=original_quantity,
            returned_quantity=returned_quantity,
            returnable_quantity=returnable_quantity,
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
    ) -> ListReturnExecutionLineDTO:
        """Передаёт SQL-сумму распределений только одной строки одного исполнения."""
        return ListReturnExecutionLineDTO(
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
    ) -> ReturnSourceItemDTO:
        """Передаёт текущую физическую позицию; даты берутся только из партии."""
        return ReturnSourceItemDTO(
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

    @staticmethod
    def to_destination(location: StockLocationModel) -> ReturnDestinationDTO:
        """Преобразует конкретную ORM-модель в подпись назначения."""
        return ReturnDestinationDTO(location.id, location.code, location.name)
