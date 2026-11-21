from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanTimeError,
    FulfillmentShipmentProgressMismatchError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.shipment.fulfillment_snapshot import (
    ShipmentFulfillmentSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO


class FulfillmentShipmentProgressPolicy:
    """Сопоставляет полный накопленный факт Shipment с неизменными распределениями без текущих удержаний."""

    @staticmethod
    def ensure_compatible(
        *,
        plan_id: FulfillmentPlanIdVO,
        plan_version: int,
        plan_status: FulfillmentPlanStatus,
        order_ref: FulfillmentOrderRefVO,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocation, ...],
        shipment: ShipmentFulfillmentSnapshot,
        as_of: datetime,
    ) -> None:
        """Проверяет заказ, область, основание, полный закреплённый состав Shipment и идентичность каждой плановой строки."""
        if (
            not isinstance(plan_id, FulfillmentPlanIdVO)
            or type(plan_version) is not int
            or plan_version < 0
            or not isinstance(order_ref, FulfillmentOrderRefVO)
            or not isinstance(owner_id, StockOwnerIdVO)
            or plan_status
            not in (
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
                FulfillmentPlanStatus.FULFILLED,
            )
            or not isinstance(plan_status, FulfillmentPlanStatus)
            or not isinstance(allocations, tuple)
            or not isinstance(shipment, ShipmentFulfillmentSnapshot)
        ):
            raise FulfillmentShipmentProgressMismatchError(
                "Нужны подтверждённый план, его распределения и специализированный факт Shipment."
            )
        shipment.ensure_valid()
        source = shipment.fulfillment_source
        if (
            source.plan_id != plan_id
            or source.plan_version > plan_version
            or shipment.owner_id != owner_id
            or shipment.order_ref
            != ShipmentOrderRefVO(order_ref.system, order_ref.reference)
        ):
            raise FulfillmentShipmentProgressMismatchError(
                "План, историческая версия основания, заказ или владелец не совпадают."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < shipment.updated_at
        ):
            raise FulfillmentPlanTimeError(
                "Регистрация в UTC не может предшествовать текущему состоянию Shipment."
            )
        selected, ids = {}, set()
        for allocation in allocations:
            if not isinstance(allocation, FulfillmentAllocation):
                raise FulfillmentShipmentProgressMismatchError(
                    "Нужны дочерние распределения FulfillmentPlan."
                )
            allocation.ensure_valid()
            if allocation.id in ids:
                raise FulfillmentShipmentProgressMismatchError(
                    "Распределение плана повторяется."
                )
            ids.add(allocation.id)
            if (
                allocation.shipment_assignment is not None
                and allocation.shipment_assignment.shipment_id == shipment.id
            ):
                if allocation.source.warehouse_id != shipment.warehouse_id:
                    raise FulfillmentShipmentProgressMismatchError(
                        "Одно Shipment не может исполнять разные склады."
                    )
                selected[allocation.id] = allocation
        if not selected or set(selected) != {
            line.fulfillment_allocation_id for line in shipment.lines
        }:
            raise FulfillmentShipmentProgressMismatchError(
                "Нужны ровно все Allocation, закреплённые за этим Shipment, включая строки без отгрузки."
            )
        for line in shipment.lines:
            allocation = selected[line.fulfillment_allocation_id]
            if (
                allocation.reservation is None
                or line.source_ref != allocation.source_ref
                or line.reservation_id != allocation.reservation.reservation_id
                or line.inventory_item_id != allocation.inventory_item_id
                or line.base_uom != allocation.base_uom
                or line.planned_qty != allocation.quantity
            ):
                raise FulfillmentShipmentProgressMismatchError(
                    "Резерв, строка заказа, товар, единица или плановое количество распределения изменены."
                )
