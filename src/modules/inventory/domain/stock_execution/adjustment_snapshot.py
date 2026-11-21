from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.policy.stock_adjustment_routes import (
    StockAdjustmentRoutesPolicy,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.value_object.adjustment_route import (
    StockAdjustmentExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockAdjustmentExecutionLineSnapshot:
    """Сохраняет одну полную фактическую поправку с исходной строкой и разрешённой позицией."""

    id: StockExecutionLineIdVO
    document_line_id: StockDocumentLineIdVO
    base_uom: UomCodeVO
    route: StockAdjustmentExecutionRouteVO

    def as_line(self) -> StockExecutionLine:
        """Проверяет локальные значения исторической фабрикой без восстановления агрегата исполнения."""
        if not isinstance(self.route, StockAdjustmentExecutionRouteVO):
            raise StockAdjustmentError("Нужен фактический маршрут корректировки.")
        quantity = QuantityVO(self.route.adjustment.quantity_delta.value.copy_abs())
        return StockExecutionLine.restore(
            identifier=self.id,
            document_line_id=self.document_line_id,
            inventory_item_id=self.route.adjustment.dimensions.inventory_item_id,
            base_uom=self.base_uom,
            quantity=quantity,
            conversion=QuantityConversionSnapshotVO(
                quantity, self.base_uom, Decimal(1)
            ),
            route=self.route,
        )


@dataclass(frozen=True, slots=True)
class StockAdjustmentExecutionSnapshot:
    """Передаёт полный факт корректировки для Ledger и регистрации без потери знаков и целей."""

    id: StockExecutionIdVO
    document_id: StockDocumentIdVO
    document_version: int
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockAdjustmentExecutionLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет типы, UTC, уникальность строк документа/факта и физические направления SERIAL."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.document_id, StockDocumentIdVO)
            or type(self.document_version) is not int
            or self.document_version < 0
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise StockAdjustmentError(
                "Нужен полный снимок корректировки с версией основания и UTC-временем."
            )
        identifiers, documents, routes = set(), set(), []
        for row in self.lines:
            if not isinstance(row, StockAdjustmentExecutionLineSnapshot):
                raise StockAdjustmentError(
                    "Нужны фактические снимки строк корректировки."
                )
            row.as_line()
            if (
                row.id in identifiers
                or row.document_line_id in documents
                or row.route.adjustment.dimensions.owner_id != self.owner_id
            ):
                raise StockAdjustmentError(
                    "Строки документа/факта уникальны и принадлежат владельцу исполнения."
                )
            identifiers.add(row.id)
            documents.add(row.document_line_id)
            routes.append(row.route)
        StockAdjustmentRoutesPolicy.ensure_valid(tuple(routes))
