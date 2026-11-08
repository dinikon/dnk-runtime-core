from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentShipmentAssignmentConflictError,
    FulfillmentPlanTimeError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.shipment.assignment_snapshot import (
    ShipmentAssignmentSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO


class FulfillmentShipmentAssignmentPolicy:
    """Проверяет выбранное назначение Shipment и отмену черновика без чтения других агрегатов или удержаний."""

    @staticmethod
    def ensure_assignable(
        *,
        plan_id: FulfillmentPlanIdVO,
        plan_version: int,
        order_ref: FulfillmentOrderRefVO,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocation, ...],
        shipment: ShipmentAssignmentSnapshot,
        as_of: datetime,
    ) -> None:
        """Требует DRAFT с выбранными свободными Allocation либо точный повтор всей прежней группы."""
        selected = FulfillmentShipmentAssignmentPolicy._selected(
            plan_id=plan_id,
            plan_version=plan_version,
            order_ref=order_ref,
            owner_id=owner_id,
            allocations=allocations,
            shipment=shipment,
            as_of=as_of,
        )
        if shipment.status is not ShipmentStatus.DRAFT:
            raise FulfillmentShipmentAssignmentConflictError(
                "Назначить можно только производный DRAFT."
            )
        by_id = {row.fulfillment_allocation_id: row for row in shipment.lines}
        for row in selected:
            previous = row.shipment_assignment
            if previous is not None and (
                previous.shipment_id,
                previous.shipment_line_id,
                previous.shipment_version,
                previous.source_plan_version,
            ) != (
                shipment.id,
                by_id[row.id].id,
                shipment.version,
                shipment.fulfillment_source.plan_version,
            ):
                raise FulfillmentShipmentAssignmentConflictError(
                    "Распределение уже назначено другому Shipment, строке или версии черновика."
                )

    @staticmethod
    def ensure_releasable(
        *,
        plan_id: FulfillmentPlanIdVO,
        plan_version: int,
        order_ref: FulfillmentOrderRefVO,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocation, ...],
        shipment: ShipmentAssignmentSnapshot,
        as_of: datetime,
    ) -> None:
        """Требует отмену прежнего черновика более новой версией; старое снятие не затрагивает новое назначение."""
        selected = FulfillmentShipmentAssignmentPolicy._selected(
            plan_id=plan_id,
            plan_version=plan_version,
            order_ref=order_ref,
            owner_id=owner_id,
            allocations=allocations,
            shipment=shipment,
            as_of=as_of,
        )
        if shipment.status is not ShipmentStatus.CANCELLED:
            raise FulfillmentShipmentAssignmentConflictError(
                "Снять назначение можно только по CANCELLED-черновику."
            )
        by_id = {row.fulfillment_allocation_id: row for row in shipment.lines}
        for row in selected:
            assignment = row.shipment_assignment
            if assignment is None:
                continue
            if (
                (
                    assignment.shipment_id,
                    assignment.shipment_line_id,
                    assignment.source_plan_version,
                )
                != (
                    shipment.id,
                    by_id[row.id].id,
                    shipment.fulfillment_source.plan_version,
                )
                or shipment.version <= assignment.shipment_version
                or shipment.updated_at < assignment.assigned_at
            ):
                raise FulfillmentShipmentAssignmentConflictError(
                    "Отмена не соответствует прежнему назначению или его версии/времени."
                )

    @staticmethod
    def _selected(
        *,
        plan_id: FulfillmentPlanIdVO,
        plan_version: int,
        order_ref: FulfillmentOrderRefVO,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocation, ...],
        shipment: ShipmentAssignmentSnapshot,
        as_of: datetime,
    ) -> tuple[FulfillmentAllocation, ...]:
        """Сопоставляет явный состав черновика и защищает полный набор уже назначенной ему группы."""
        if (
            not isinstance(plan_id, FulfillmentPlanIdVO)
            or type(plan_version) is not int
            or plan_version < 0
            or not isinstance(order_ref, FulfillmentOrderRefVO)
            or not isinstance(owner_id, StockOwnerIdVO)
            or not isinstance(allocations, tuple)
            or not isinstance(shipment, ShipmentAssignmentSnapshot)
        ):
            raise FulfillmentShipmentAssignmentConflictError(
                "Нужны типизированные данные плана и специализированный снимок назначения."
            )
        shipment.ensure_valid()
        if (
            shipment.fulfillment_source.plan_id != plan_id
            or shipment.fulfillment_source.plan_version > plan_version
            or shipment.owner_id != owner_id
            or shipment.order_ref
            != ShipmentOrderRefVO(order_ref.system, order_ref.reference)
        ):
            raise FulfillmentShipmentAssignmentConflictError(
                "Основание, заказ, владелец или версия не соответствуют плану."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < shipment.updated_at
        ):
            raise FulfillmentPlanTimeError(
                "Назначение или снятие в UTC не может предшествовать состоянию Shipment."
            )
        requested = {line.fulfillment_allocation_id for line in shipment.lines}
        selected, assigned_group = {}, set()
        ids = set()
        for row in allocations:
            if not isinstance(row, FulfillmentAllocation):
                raise FulfillmentShipmentAssignmentConflictError(
                    "Нужны дочерние распределения."
                )
            row.ensure_valid()
            if row.id in ids:
                raise FulfillmentShipmentAssignmentConflictError(
                    "Распределение повторяется."
                )
            ids.add(row.id)
            if row.id in requested:
                if (
                    not isinstance(row.source, FulfillmentSourceRefVO)
                    or row.source.warehouse_id != shipment.warehouse_id
                ):
                    raise FulfillmentShipmentAssignmentConflictError(
                        "Назначение Shipment относится к указанному собственному складу."
                    )
                selected[row.id] = row
            if (
                row.shipment_assignment is not None
                and row.shipment_assignment.shipment_id == shipment.id
            ):
                assigned_group.add(row.id)
        if set(selected) != requested or (
            assigned_group and assigned_group != requested
        ):
            raise FulfillmentShipmentAssignmentConflictError(
                "Нужны известные выбранные Allocation и ровно весь прежний состав назначенного Shipment."
            )
        for line in shipment.lines:
            row = selected[line.fulfillment_allocation_id]
            if (
                row.status is not FulfillmentAllocationStatus.CONFIRMED
                or row.shipment_progress is not None
                or row.reservation is None
                or not row.fulfilled_qty.value.is_zero()
                or line.source_ref != row.source_ref
                or line.reservation_id != row.reservation.reservation_id
                or line.inventory_item_id != row.inventory_item_id
                or line.base_uom != row.base_uom
                or line.planned_qty != row.quantity
            ):
                raise FulfillmentShipmentAssignmentConflictError(
                    "Назначение требует прежние подтверждённые неисполненные распределения без изменения состава."
                )
        return tuple(selected.values())
