from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    QuantityConversionMismatchError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionPostingSnapshotError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockExecutionPostingLineSnapshot:
    """Сохраняет детализацию фактической строки для Ledger без плановых количеств и чужих Entity."""

    id: StockExecutionLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    conversion: QuantityConversionSnapshotVO
    route: (
        ReceiptExecutionRouteVO | IssueExecutionRouteVO | InternalMoveExecutionRouteVO
    )

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, исходный пересчёт, маршрут и поштучную идентичность серии."""
        if (
            not isinstance(self.id, StockExecutionLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.conversion, QuantityConversionSnapshotVO)
            or not isinstance(
                self.route,
                (
                    ReceiptExecutionRouteVO,
                    IssueExecutionRouteVO,
                    InternalMoveExecutionRouteVO,
                ),
            )
        ):
            raise InvalidStockExecutionPostingSnapshotError(
                "Нужны типизированные фактические строки с положительным количеством и маршрутом."
            )
        if (
            get_uom(self.base_uom).dimension
            is not get_uom(self.conversion.uom).dimension
        ):
            raise IncompatibleUomError(
                "Исходная и базовая единицы факта должны иметь одну размерность."
            )
        if self.conversion.to_base_quantity() != self.quantity:
            raise QuantityConversionMismatchError(
                "Фактическое количество не соответствует сохранённому пересчёту."
            )
        for dimensions in self.route.dimensions:
            if dimensions.inventory_item_id != self.inventory_item_id:
                raise InvalidStockExecutionPostingSnapshotError(
                    "Товар маршрута не соответствует фактической строке."
                )
            if dimensions.serial_id is not None and (
                self.base_uom != UomCodeVO("PCS") or self.quantity.value != Decimal(1)
            ):
                raise InvalidStockExecutionPostingSnapshotError(
                    "Конкретный серийный экземпляр требует 1 PCS."
                )


@dataclass(frozen=True, slots=True)
class StockExecutionPostingSnapshot:
    """Передаёт неизменяемое основание и полные физические маршруты для построения проведения."""

    id: StockExecutionIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockExecutionPostingLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет реквизиты, UTC-время, вид маршрута и уникальность строк и серий."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockExecutionPostingSnapshotError(
                "Нужен непустой типизированный снимок исполнения с временем UTC."
            )
        expected_route = {
            StockOperationType.RECEIPT: ReceiptExecutionRouteVO,
            StockOperationType.ISSUE: IssueExecutionRouteVO,
            StockOperationType.INTERNAL_MOVE: InternalMoveExecutionRouteVO,
        }.get(self.operation_type)
        ids, serials = set(), set()
        for line in self.lines:
            if not isinstance(line, StockExecutionPostingLineSnapshot):
                raise InvalidStockExecutionPostingSnapshotError(
                    "Нужны снимки строк, а не Entity фактического исполнения."
                )
            line.ensure_valid()
            if (
                line.id in ids
                or expected_route is None
                or not isinstance(line.route, expected_route)
            ):
                raise InvalidStockExecutionPostingSnapshotError(
                    "ID строк должны быть уникальны, а маршрут соответствовать операции."
                )
            ids.add(line.id)
            line_serials = set()
            for dimensions in line.route.dimensions:
                if dimensions.owner_id != self.owner_id:
                    raise InvalidStockExecutionPostingSnapshotError(
                        "Владелец маршрута не соответствует исполнению."
                    )
                if dimensions.serial_id is not None:
                    line_serials.add(dimensions.serial_id)
            if serials.intersection(line_serials):
                raise InvalidStockExecutionPostingSnapshotError(
                    "Один экземпляр нельзя повторять в разных фактических строках."
                )
            serials.update(line_serials)
