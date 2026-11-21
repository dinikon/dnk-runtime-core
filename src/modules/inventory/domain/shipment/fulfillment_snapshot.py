from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentFulfillmentSnapshotError,
)
from src.modules.inventory.domain.shipment.execution_snapshot import (
    ShipmentExecutionPlanLineSnapshot,
    ShipmentExecutionPlanSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_source import (
    ShipmentFulfillmentSourceVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class ShipmentFulfillmentLineSnapshot:
    """Передаёт происхождение и накопленный прогресс каждой строки производной отгрузки."""

    id: ShipmentLineIdVO
    fulfillment_allocation_id: FulfillmentAllocationIdVO
    source_ref: ReservationSourceVO
    reservation_id: StockReservationIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    shipped_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет локальную привязку и диапазон количества по прежнему контракту прогресса Shipment."""
        if not isinstance(
            self.fulfillment_allocation_id, FulfillmentAllocationIdVO
        ) or not isinstance(self.source_ref, ReservationSourceVO):
            raise InvalidShipmentFulfillmentSnapshotError(
                "Нужны типизированные распределение и строка заказа."
            )
        ShipmentExecutionPlanLineSnapshot(
            self.id,
            self.inventory_item_id,
            self.base_uom,
            self.reservation_id,
            self.planned_qty,
            self.shipped_qty,
        ).ensure_valid()


@dataclass(frozen=True, slots=True)
class ShipmentFulfillmentSnapshot:
    """Передаёт весь состав уже частично или полностью отгруженного Shipment для регистрации в плане."""

    id: ShipmentIdVO
    version: int
    status: ShipmentStatus
    fulfillment_source: ShipmentFulfillmentSourceVO
    order_ref: ShipmentOrderRefVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    updated_at: datetime
    lines: tuple[ShipmentFulfillmentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует производное отправление с фактом, уникальные распределения и полный согласованный состав."""
        if (
            not isinstance(self.fulfillment_source, ShipmentFulfillmentSourceVO)
            or not isinstance(self.order_ref, ShipmentOrderRefVO)
            or self.status
            not in (ShipmentStatus.PARTIALLY_SHIPPED, ShipmentStatus.SHIPPED)
            or not isinstance(self.status, ShipmentStatus)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidShipmentFulfillmentSnapshotError(
                "Нужны основание, заказ и весь tuple строк частично/полностью отгруженного Shipment."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, ShipmentFulfillmentLineSnapshot):
                raise InvalidShipmentFulfillmentSnapshotError(
                    "Нужны специализированные снимки всех строк отгрузки."
                )
            line.ensure_valid()
            if line.fulfillment_allocation_id in ids:
                raise InvalidShipmentFulfillmentSnapshotError(
                    "Распределение повторяется в отправлении."
                )
            ids.add(line.fulfillment_allocation_id)
        ShipmentExecutionPlanSnapshot(
            self.id,
            self.version,
            self.status,
            self.warehouse_id,
            self.owner_id,
            self.updated_at,
            tuple(
                ShipmentExecutionPlanLineSnapshot(
                    line.id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.reservation_id,
                    line.planned_qty,
                    line.shipped_qty,
                )
                for line in self.lines
            ),
        ).ensure_valid()
