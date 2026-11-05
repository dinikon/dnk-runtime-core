from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.policy.inventory_count_adjustment_document import (
    InventoryCountAdjustmentDocumentPolicy,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockDocumentAdjustmentLineSnapshot:
    """Передаёт собственные значения подтверждённой строки без чужой Entity."""

    id: StockDocumentLineIdVO
    sku: SkuVO
    base_uom: UomCodeVO
    adjustment: StockAdjustmentLineVO
    source: DocumentLineSourceVO

    def as_line(self) -> StockDocumentLine:
        """Проверяет локальный состав прежней фабрикой строки без восстановления корня документа."""
        if not isinstance(self.adjustment, StockAdjustmentLineVO):
            raise StockAdjustmentError("Нужно основание строки корректировки.")
        quantity = QuantityVO(self.adjustment.quantity_delta.value.copy_abs())
        return StockDocumentLine.restore(
            identifier=self.id,
            inventory_item_id=self.adjustment.dimensions.inventory_item_id,
            sku=self.sku,
            base_uom=self.base_uom,
            planned_qty=quantity,
            conversion=QuantityConversionSnapshotVO(
                quantity, self.base_uom, Decimal(1)
            ),
            executed_qty=QuantityVO(Decimal(0)),
            source=self.source,
            adjustment=self.adjustment,
        )


@dataclass(frozen=True, slots=True)
class StockDocumentAdjustmentExecutionSnapshot:
    """Фиксирует только подтверждённый неисполненный план со знаками, целями и происхождением."""

    id: StockDocumentIdVO
    version: int
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: StockDocumentStatus
    updated_at: datetime
    source: DocumentSourceVO
    lines: tuple[StockDocumentAdjustmentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует CONFIRMED, строгую версию, UTC и полный уникальный состав исходных поправок."""
        if (
            not isinstance(self.id, StockDocumentIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or self.status is not StockDocumentStatus.CONFIRMED
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.source, DocumentSourceVO)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise StockAdjustmentError(
                "Нужен подтверждённый план корректировки с версией и UTC-временем."
            )
        lines = []
        identifiers = set()
        for row in self.lines:
            if not isinstance(row, StockDocumentAdjustmentLineSnapshot):
                raise StockAdjustmentError("Нужны снимки строк корректировки.")
            line = row.as_line()
            if line.id in identifiers:
                raise StockAdjustmentError("ID строки плана повторяется.")
            identifiers.add(line.id)
            lines.append(line)
        InventoryCountAdjustmentDocumentPolicy.ensure_document_source(
            operation_type=StockOperationType.ADJUSTMENT,
            source=self.source,
            owner_id=self.owner_id,
            status=self.status,
            lines=tuple(lines),
        )
