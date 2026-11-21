from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentExecutionPlanSnapshotError,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class ShipmentExecutionPlanLineSnapshot:
    """Передаёт неизменяемую привязку, план и накопленное количество строки отгрузки."""

    id: ShipmentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    reservation_id: StockReservationIdVO
    planned_qty: QuantityVO
    shipped_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Требует положительный план и собственный прогресс от нуля до планового количества."""
        if (
            not isinstance(self.id, ShipmentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.reservation_id, StockReservationIdVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.shipped_qty, QuantityVO)
            or self.shipped_qty.value > self.planned_qty.value
        ):
            raise InvalidShipmentExecutionPlanSnapshotError(
                "Некорректная строка снимка плана отгрузки."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class ShipmentExecutionPlanSnapshot:
    """Передаёт текущую версию плана без чужого корня и полной истории исполнений."""

    id: ShipmentIdVO
    version: int
    status: ShipmentStatus
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    updated_at: datetime
    lines: tuple[ShipmentExecutionPlanLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет типы, UTC, уникальность привязок и согласованность прогресса со статусом."""
        if (
            not isinstance(self.id, ShipmentIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, ShipmentStatus)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidShipmentExecutionPlanSnapshotError(
                "Нужен типизированный снимок плана с версией и UTC-временем."
            )
        ids, reservations = set(), set()
        for line in self.lines:
            if not isinstance(line, ShipmentExecutionPlanLineSnapshot):
                raise InvalidShipmentExecutionPlanSnapshotError(
                    "Нужны снимки строк плана."
                )
            line.ensure_valid()
            if line.id in ids or line.reservation_id in reservations:
                raise InvalidShipmentExecutionPlanSnapshotError(
                    "Строки и резервы снимка не должны повторяться."
                )
            ids.add(line.id)
            reservations.add(line.reservation_id)
        any_shipped = any(not line.shipped_qty.value.is_zero() for line in self.lines)
        complete = bool(self.lines) and all(
            line.shipped_qty == line.planned_qty for line in self.lines
        )
        if (
            (
                self.status not in (ShipmentStatus.DRAFT, ShipmentStatus.CANCELLED)
                and not self.lines
            )
            or (
                self.status
                in (
                    ShipmentStatus.DRAFT,
                    ShipmentStatus.CONFIRMED,
                    ShipmentStatus.CANCELLED,
                )
                and any_shipped
            )
            or (
                self.status is ShipmentStatus.PARTIALLY_SHIPPED
                and (not any_shipped or complete)
            )
            or (self.status is ShipmentStatus.SHIPPED and not complete)
        ):
            raise InvalidShipmentExecutionPlanSnapshotError(
                "Статус снимка не соответствует прогрессу отгрузки."
            )
