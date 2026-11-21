from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.policy.inventory_count_adjustment_document import (
    InventoryCountAdjustmentDocumentPolicy,
)
from src.modules.inventory.domain.policy.stock_document_progress import (
    StockDocumentProgressPolicy,
)
from src.modules.inventory.domain.stock_document.adjustment_execution_snapshot import (
    StockDocumentAdjustmentLineSnapshot,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockDocumentAdjustmentCompletionLineSnapshot:
    """Передаёт историческую поправку и реальные плановое/исполненное количества завершённой строки."""

    line: StockDocumentAdjustmentLineSnapshot
    planned_qty: QuantityVO
    executed_qty: QuantityVO

    def as_line(self) -> StockDocumentLine:
        """Проверяет собственные значения строки без восстановления статуса или чужого корня."""
        if not isinstance(self.line, StockDocumentAdjustmentLineSnapshot):
            raise StockAdjustmentError(
                "Нужен снимок исходных значений строки корректировки."
            )
        original = self.line.as_line()
        return StockDocumentLine.restore(
            identifier=original.id,
            inventory_item_id=original.inventory_item_id,
            sku=original.sku,
            base_uom=original.base_uom,
            planned_qty=self.planned_qty,
            conversion=original.conversion,
            executed_qty=self.executed_qty,
            source=original.source,
            adjustment=original.adjustment,
        )


@dataclass(frozen=True, slots=True)
class StockDocumentAdjustmentCompletionSnapshot:
    """Представляет завершённую корректировку без подмены её статуса на CONFIRMED."""

    id: StockDocumentIdVO
    version: int
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: StockDocumentStatus
    updated_at: datetime
    source: DocumentSourceVO
    lines: tuple[StockDocumentAdjustmentCompletionLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует COMPLETED, UTC, строгую версию и полностью исполненный уникальный состав."""
        if (
            not isinstance(self.id, StockDocumentIdVO)
            or type(self.version) is not int
            or self.version < 1
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or self.status is not StockDocumentStatus.COMPLETED
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.source, DocumentSourceVO)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise StockAdjustmentError(
                "Нужен завершённый документ ADJUSTMENT с UTC-временем и положительной версией."
            )
        lines, identifiers = [], set()
        for row in self.lines:
            if not isinstance(row, StockDocumentAdjustmentCompletionLineSnapshot):
                raise StockAdjustmentError(
                    "Нужны снимки завершённых строк корректировки."
                )
            line = row.as_line()
            if line.id in identifiers:
                raise StockAdjustmentError("Строка завершённого документа повторяется.")
            identifiers.add(line.id)
            lines.append(line)
        InventoryCountAdjustmentDocumentPolicy.ensure_document_source(
            operation_type=StockOperationType.ADJUSTMENT,
            source=self.source,
            owner_id=self.owner_id,
            status=self.status,
            lines=tuple(lines),
        )
        StockDocumentProgressPolicy.ensure_valid(
            status=self.status,
            quantities=tuple((line.planned_qty, line.executed_qty) for line in lines),
        )
