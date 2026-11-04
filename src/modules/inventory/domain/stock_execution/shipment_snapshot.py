from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionShipmentSnapshotError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockExecutionShipmentLineSnapshot:
    """Передаёт целую фактическую строку вместе с ID плановой строки её документа."""

    execution_line_id: StockExecutionLineIdVO
    document_line_id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO

    def ensure_valid(self) -> None:
        """Требует типизированные ссылки, известную единицу и положительное базовое количество."""
        if (
            not isinstance(self.execution_line_id, StockExecutionLineIdVO)
            or not isinstance(self.document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
        ):
            raise InvalidStockExecutionShipmentSnapshotError(
                "Нужна типизированная фактическая строка с положительным количеством и связью с документом."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class StockExecutionShipmentSnapshot:
    """Передаёт версию документа и все фактические строки для автоматического назначения отгрузке."""

    id: StockExecutionIdVO
    document_id: StockDocumentIdVO
    document_version: int
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockExecutionShipmentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет строгую версию, UTC и уникальность фактических ID, допуская несколько фактов на строку плана."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.document_id, StockDocumentIdVO)
            or type(self.document_version) is not int
            or self.document_version < 0
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockExecutionShipmentSnapshotError(
                "Нужен непустой типизированный снимок факта с версией документа и UTC-временем."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, StockExecutionShipmentLineSnapshot):
                raise InvalidStockExecutionShipmentSnapshotError(
                    "Нужны снимки фактических строк для Shipment."
                )
            line.ensure_valid()
            if line.execution_line_id in ids:
                raise InvalidStockExecutionShipmentSnapshotError(
                    "ID фактических строк не должны повторяться."
                )
            ids.add(line.execution_line_id)
