from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentAssignmentSnapshotError,
)
from src.modules.inventory.domain.shipment.fulfillment_snapshot import (
    ShipmentFulfillmentLineSnapshot,
)
from src.modules.inventory.domain.shipment.execution_snapshot import (
    ShipmentExecutionPlanSnapshot,
    ShipmentExecutionPlanLineSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.fulfillment_source import (
    ShipmentFulfillmentSourceVO,
)
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ShipmentAssignmentLineSnapshot:
    """Передаёт идентичность и количества строки только для назначения неисполненного черновика."""

    id: ShipmentLineIdVO
    fulfillment_allocation_id: FulfillmentAllocationIdVO
    source_ref: ReservationSourceVO
    reservation_id: StockReservationIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    shipped_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет исходные привязки и требует нулевое фактическое количество."""
        ShipmentFulfillmentLineSnapshot(
            self.id,
            self.fulfillment_allocation_id,
            self.source_ref,
            self.reservation_id,
            self.inventory_item_id,
            self.base_uom,
            self.planned_qty,
            self.shipped_qty,
        ).ensure_valid()
        if not self.shipped_qty.value.is_zero():
            raise InvalidShipmentAssignmentSnapshotError(
                "Назначение или снятие требует нулевое исполнение."
            )


@dataclass(frozen=True, slots=True)
class ShipmentAssignmentSnapshot:
    """Передаёт полный производный DRAFT/CANCELLED для назначения или снятия без ссылки на чужой агрегат."""

    id: ShipmentIdVO
    version: int
    status: ShipmentStatus
    fulfillment_source: ShipmentFulfillmentSourceVO
    order_ref: ShipmentOrderRefVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    updated_at: datetime
    lines: tuple[ShipmentAssignmentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет нулевой прогресс, номинальные поля, строгую версию, UTC и уникальность полного состава."""
        if (
            self.status not in (ShipmentStatus.DRAFT, ShipmentStatus.CANCELLED)
            or not isinstance(self.status, ShipmentStatus)
            or not isinstance(self.fulfillment_source, ShipmentFulfillmentSourceVO)
            or not isinstance(self.order_ref, ShipmentOrderRefVO)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidShipmentAssignmentSnapshotError(
                "Нужен непустой производный DRAFT/CANCELLED с основанием и заказом."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, ShipmentAssignmentLineSnapshot):
                raise InvalidShipmentAssignmentSnapshotError(
                    "Нужны строки снимка назначения."
                )
            line.ensure_valid()
            if line.fulfillment_allocation_id in ids:
                raise InvalidShipmentAssignmentSnapshotError(
                    "Распределение повторяется."
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
                    row.id,
                    row.inventory_item_id,
                    row.base_uom,
                    row.reservation_id,
                    row.planned_qty,
                    row.shipped_qty,
                )
                for row in self.lines
            ),
        ).ensure_valid()
