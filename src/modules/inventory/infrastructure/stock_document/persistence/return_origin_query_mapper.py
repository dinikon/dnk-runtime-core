from decimal import Decimal
from src.modules.inventory.application.stock_document.query.get_return_origin.dto import (
    GetReturnOriginLineDTO,
    GetReturnOriginResultDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
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
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)


class ReturnOriginQueryMapper:
    """Преобразует типизированную проекцию основания без SQL и бизнес-решений."""

    @staticmethod
    def to_details(
        execution: StockExecutionModel,
        warehouse: WarehouseModel,
        *,
        direction: str,
        lines: tuple[GetReturnOriginLineDTO, ...],
    ) -> GetReturnOriginResultDTO:
        """Передаёт направление, проверенное вызывающим сценарием, и точные строки."""
        return GetReturnOriginResultDTO(
            execution.id,
            execution.document_id,
            execution.operation_type,
            direction,
            execution.warehouse_id,
            warehouse.code,
            warehouse.name,
            execution.owner_id,
            lines,
        )

    @staticmethod
    def to_line(
        line: StockExecutionLineModel,
        item: InventoryItemModel,
        location: StockLocationModel,
        lot: StockLotModel | None,
        serial: StockSerialModel | None,
        returned: Decimal,
        remaining: Decimal,
    ) -> GetReturnOriginLineDTO:
        """Сохраняет фактические количества и идентичность с актуальными подписями."""
        return GetReturnOriginLineDTO(
            line.id,
            line.position,
            line.inventory_item_id,
            item.sku,
            line.base_uom,
            line.quantity,
            returned,
            remaining,
            line.location_id,
            location.code,
            line.stock_status,
            line.lot_id,
            lot.number if lot else None,
            line.serial_id,
            serial.number if serial else None,
        )
