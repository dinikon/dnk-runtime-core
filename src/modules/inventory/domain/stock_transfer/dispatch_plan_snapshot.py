from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferDispatchPlanSnapshotError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.stock_transfer.value_object.transit import (
    StockTransferTransitVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockTransferDispatchPlanLineSnapshot:
    """Передаёт план и накопленную отправку одной строки перемещения."""

    id: StockTransferLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    dispatched_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы и диапазон отправленного количества."""
        if (
            not isinstance(self.id, StockTransferLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.dispatched_qty, QuantityVO)
            or self.dispatched_qty.value > self.planned_qty.value
        ):
            raise InvalidStockTransferDispatchPlanSnapshotError(
                "Некорректная строка плана отправки."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class StockTransferDispatchPlanSnapshot:
    """Передаёт текущую версию, направление, зафиксированный транзит и прогресс без чужого корня."""

    id: StockTransferIdVO
    version: int
    status: StockTransferStatus
    source_warehouse_id: WarehouseIdVO
    destination_warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    transit: StockTransferTransitVO | None
    updated_at: datetime
    lines: tuple[StockTransferDispatchPlanLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет UTC, строгую версию, направление, уникальность строк и согласованность состояния."""
        if (
            not isinstance(self.id, StockTransferIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, StockTransferStatus)
            or not isinstance(self.source_warehouse_id, WarehouseIdVO)
            or not isinstance(self.destination_warehouse_id, WarehouseIdVO)
            or self.source_warehouse_id == self.destination_warehouse_id
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or (
                self.transit is not None
                and not isinstance(self.transit, StockTransferTransitVO)
            )
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockTransferDispatchPlanSnapshotError(
                "Нужен типизированный снимок плана отправки с UTC-временем и строгой версией."
            )
        if self.transit is not None and self.transit.warehouse_id in (
            self.source_warehouse_id,
            self.destination_warehouse_id,
        ):
            raise InvalidStockTransferDispatchPlanSnapshotError(
                "Транзитный склад должен отличаться от обоих конечных."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, StockTransferDispatchPlanLineSnapshot):
                raise InvalidStockTransferDispatchPlanSnapshotError(
                    "Нужны снимки плановых строк отправки."
                )
            line.ensure_valid()
            if line.id in ids:
                raise InvalidStockTransferDispatchPlanSnapshotError(
                    "Строки плана отправки не должны повторяться."
                )
            ids.add(line.id)
        any_sent = any(not line.dispatched_qty.value.is_zero() for line in self.lines)
        if (
            (
                self.status
                in (
                    StockTransferStatus.CONFIRMED,
                    StockTransferStatus.IN_PROGRESS,
                    StockTransferStatus.COMPLETED,
                )
                and not self.lines
            )
            or (
                self.status
                in (StockTransferStatus.IN_PROGRESS, StockTransferStatus.COMPLETED)
                and (not any_sent or self.transit is None)
            )
            or (
                self.status
                not in (StockTransferStatus.IN_PROGRESS, StockTransferStatus.COMPLETED)
                and (any_sent or self.transit is not None)
            )
            or (
                self.status is StockTransferStatus.COMPLETED
                and any(line.dispatched_qty != line.planned_qty for line in self.lines)
            )
        ):
            raise InvalidStockTransferDispatchPlanSnapshotError(
                "Состояние плана не соответствует отправке и транзитному маршруту."
            )
