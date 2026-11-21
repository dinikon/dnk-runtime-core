from collections.abc import Sequence
from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnOriginSnapshot,
    StockReturnOriginLineSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)


class ReturnOriginMapper:
    """Преобразует собственную SQL-проекцию в специализированный бизнес-снимок без I/O."""

    @staticmethod
    def to_snapshot(
        execution: StockExecutionModel,
        document: StockDocumentModel,
        posting: StockPostingModel | None,
        lines: Sequence[StockExecutionLineModel],
        compensated: bool,
    ) -> StockReturnOriginSnapshot:
        """Сохраняет действительные фактические строки, не подменяя их агрегированным Ledger."""
        return StockReturnOriginSnapshot(
            StockExecutionIdVO(execution.id),
            StockOperationType(execution.operation_type),
            WarehouseIdVO(execution.warehouse_id),
            StockOwnerIdVO(execution.owner_id),
            execution.executed_at,
            StockPostingIdVO(posting.id) if posting else None,
            compensated,
            (
                DocumentSourceVO(
                    document.source_system,
                    document.source_reference,
                    document.source_version,
                )
                if document.source_system is not None
                and document.source_reference is not None
                else None
            ),
            tuple(
                StockReturnOriginLineSnapshot(
                    StockExecutionLineIdVO(line.id),
                    StockDimensionsVO(
                        InventoryItemIdVO(line.inventory_item_id),
                        StockLocationIdVO(line.location_id),
                        StockOwnerIdVO(execution.owner_id),
                        StockLotIdVO(line.lot_id) if line.lot_id else None,
                        StockSerialIdVO(line.serial_id) if line.serial_id else None,
                        StockStatus(line.stock_status),
                    ),
                    QuantityVO(line.quantity),
                    UomCodeVO(line.base_uom),
                )
                for line in lines
            ),
        )
