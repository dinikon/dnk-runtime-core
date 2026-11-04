from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferReceiptPlanSnapshotError,
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
class StockTransferReceiptPlanLineSnapshot:
    """Передаёт план, накопленные отправку и приёмку одной строки перемещения."""

    id: StockTransferLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    dispatched_qty: QuantityVO
    received_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы и диапазоны отправленного и принятого количества."""
        if (
            not isinstance(self.id, StockTransferLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.dispatched_qty, QuantityVO)
            or not isinstance(self.received_qty, QuantityVO)
            or self.received_qty.value > self.dispatched_qty.value
            or self.dispatched_qty.value > self.planned_qty.value
        ):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Некорректная строка плана приёмки."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class StockTransferReceiptPlanSnapshot:
    """Передаёт текущую версию, направление, зафиксированный транзит и прогресс без чужого корня."""

    id: StockTransferIdVO
    version: int
    status: StockTransferStatus
    source_warehouse_id: WarehouseIdVO
    destination_warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    transit: StockTransferTransitVO | None
    updated_at: datetime
    lines: tuple[StockTransferReceiptPlanLineSnapshot, ...]

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
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Нужен типизированный снимок плана приёмки с UTC-временем и строгой версией."
            )
        if self.transit is not None and self.transit.warehouse_id in (
            self.source_warehouse_id,
            self.destination_warehouse_id,
        ):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Транзитный склад должен отличаться от обоих конечных."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, StockTransferReceiptPlanLineSnapshot):
                raise InvalidStockTransferReceiptPlanSnapshotError(
                    "Нужны снимки плановых строк приёмки."
                )
            line.ensure_valid()
            if line.id in ids:
                raise InvalidStockTransferReceiptPlanSnapshotError(
                    "Строки плана приёмки не должны повторяться."
                )
            ids.add(line.id)
        any_sent = any(not line.dispatched_qty.value.is_zero() for line in self.lines)
        complete = bool(self.lines) and all(
            line.received_qty == line.planned_qty for line in self.lines
        )
        progressing = self.status in (
            StockTransferStatus.IN_PROGRESS,
            StockTransferStatus.COMPLETED,
        )
        if (
            (self.status is StockTransferStatus.CONFIRMED and not self.lines)
            or (progressing and (not any_sent or self.transit is None))
            or (not progressing and (any_sent or self.transit is not None))
            or (self.status is StockTransferStatus.COMPLETED and not complete)
            or (self.status is StockTransferStatus.IN_PROGRESS and complete)
        ):
            raise InvalidStockTransferReceiptPlanSnapshotError(
                "Состояние плана не соответствует отправке, приёмке и транзиту."
            )
