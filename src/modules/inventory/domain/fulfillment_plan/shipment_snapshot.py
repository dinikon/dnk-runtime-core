from dataclasses import dataclass
from datetime import datetime, timedelta
from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_assignment import (
    FulfillmentShipmentAssignmentRefVO,
)

from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_progress_ref import (
    FulfillmentShipmentProgressRefVO,
)

from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentPlanShipmentSnapshotError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_ref import (
    FulfillmentReservationRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_release import (
    FulfillmentReservationReleaseRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_assignment import (
    FulfillmentSupplierOrderAssignmentRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_confirmation import (
    FulfillmentSupplierOrderConfirmationRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_rejection import (
    FulfillmentSupplierOrderRejectionRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_shipment import (
    FulfillmentSupplierOrderShipmentRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class FulfillmentAllocationShipmentSnapshot:
    """Передаёт распределение и его историческое подтверждение либо отсутствие резерва без текущих удержаний."""

    id: FulfillmentAllocationIdVO
    source_ref: ReservationSourceVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    source: FulfillmentSourceRefVO | SupplierDropshipSourceRefVO
    quantity: QuantityVO
    reservation: FulfillmentReservationRefVO | None
    status: FulfillmentAllocationStatus
    fulfilled_qty: QuantityVO
    shipment_progress: FulfillmentShipmentProgressRefVO | None
    shipment_assignment: FulfillmentShipmentAssignmentRefVO | None
    reservation_releases: tuple[FulfillmentReservationReleaseRefVO, ...]
    cancelled_at: datetime | None
    quoted_purchase_price: MoneyVO | None = None
    supplier_order_assignment: FulfillmentSupplierOrderAssignmentRefVO | None = None
    supplier_confirmation: FulfillmentSupplierOrderConfirmationRefVO | None = None
    supplier_confirmed_qty: QuantityVO | None = None
    supplier_rejection: FulfillmentSupplierOrderRejectionRefVO | None = None
    supplier_shipment: FulfillmentSupplierOrderShipmentRefVO | None = None

    def ensure_valid(self) -> None:
        """Проверяет поля и матрицу подтверждения/исполнения по локальным правилам Entity."""
        if self.cancelled_at is not None and (
            not isinstance(self.cancelled_at, datetime)
            or self.cancelled_at.utcoffset() != timedelta(0)
        ):
            raise InvalidFulfillmentPlanShipmentSnapshotError(
                "Снимок хранит время отмены распределения только в UTC."
            )
        FulfillmentAllocation.restore(
            identifier=self.id,
            source_ref=self.source_ref,
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            source=self.source,
            quantity=self.quantity,
            status=self.status,
            reservation=self.reservation,
            fulfilled_qty=self.fulfilled_qty,
            shipment_progress=self.shipment_progress,
            shipment_assignment=self.shipment_assignment,
            reservation_releases=self.reservation_releases,
            cancelled_at=self.cancelled_at,
            quoted_purchase_price=self.quoted_purchase_price,
            supplier_order_assignment=self.supplier_order_assignment,
            supplier_confirmation=self.supplier_confirmation,
            supplier_confirmed_qty=self.supplier_confirmed_qty,
            supplier_rejection=self.supplier_rejection,
            supplier_shipment=self.supplier_shipment,
        )


@dataclass(frozen=True, slots=True)
class FulfillmentPlanShipmentSnapshot:
    """Передаёт частичное/полное подтверждение и прогресс для выбора готовых ещё не начатых Allocation."""

    id: FulfillmentPlanIdVO
    version: int
    status: FulfillmentPlanStatus
    order_ref: FulfillmentOrderRefVO
    owner_id: StockOwnerIdVO
    updated_at: datetime
    allocations: tuple[FulfillmentAllocationShipmentSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует активный план с подтверждениями, UTC, уникальные привязки и согласованную матрицу прогресса."""
        if (
            not isinstance(self.id, FulfillmentPlanIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, FulfillmentPlanStatus)
            or self.status
            not in (
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            )
            or not isinstance(self.order_ref, FulfillmentOrderRefVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.allocations, tuple)
            or not self.allocations
        ):
            raise InvalidFulfillmentPlanShipmentSnapshotError(
                "Нужен непустой частично/полностью подтверждённый или исполняемый план с типизированными полями, строгой версией и временем UTC."
            )
        ids, reservations, pairs, identities = set(), set(), set(), {}
        historical_reservations = set()
        for allocation in self.allocations:
            if not isinstance(allocation, FulfillmentAllocationShipmentSnapshot):
                raise InvalidFulfillmentPlanShipmentSnapshotError(
                    "Нужны специализированные снимки подтверждённых распределений."
                )
            allocation.ensure_valid()
            pair = (allocation.source_ref, allocation.source)
            identity = (allocation.inventory_item_id, allocation.base_uom)
            if (
                allocation.id in ids
                or (
                    allocation.reservation is not None
                    and (
                        allocation.reservation.reservation_id in reservations
                        or allocation.reservation.reservation_id
                        in historical_reservations
                    )
                )
                or (
                    allocation.status is not FulfillmentAllocationStatus.CANCELLED
                    and pair in pairs
                )
                or (
                    allocation.source_ref in identities
                    and identities[allocation.source_ref] != identity
                )
                or (
                    allocation.reservation is not None
                    and allocation.reservation.confirmed_at > self.updated_at
                )
                or (
                    allocation.supplier_confirmation is not None
                    and allocation.supplier_confirmation.confirmed_at > self.updated_at
                )
                or (
                    allocation.supplier_shipment is not None
                    and allocation.supplier_shipment.shipped_at > self.updated_at
                )
            ):
                raise InvalidFulfillmentPlanShipmentSnapshotError(
                    "Повтор распределения/резерва/источника, разная идентичность строки либо подтверждение из будущего."
                )
            ids.add(allocation.id)
            if allocation.reservation is not None:
                reservations.add(allocation.reservation.reservation_id)
            for release in allocation.reservation_releases:
                identifier = release.confirmation.reservation_id
                if (
                    identifier in reservations
                    or identifier in historical_reservations
                    or release.released_at > self.updated_at
                ):
                    raise InvalidFulfillmentPlanShipmentSnapshotError(
                        "История снятий требует уникальные резервные ID и не может находиться в будущем."
                    )
                historical_reservations.add(identifier)
            if allocation.status is not FulfillmentAllocationStatus.CANCELLED:
                pairs.add(pair)
            elif allocation.cancelled_at > self.updated_at:
                raise InvalidFulfillmentPlanShipmentSnapshotError(
                    "Снятие распределения не может находиться в будущем."
                )
            identities[allocation.source_ref] = identity
        active = tuple(
            row
            for row in self.allocations
            if row.status is not FulfillmentAllocationStatus.CANCELLED
        )
        any_fulfilled = any(
            not row.fulfilled_qty.value.is_zero() for row in self.allocations
        )
        all_fulfilled = all(
            row.fulfilled_qty
            == (
                row.quantity
                if row.supplier_confirmed_qty is None
                else row.supplier_confirmed_qty
            )
            for row in active
        )
        confirmed = len(reservations) + sum(
            row.supplier_confirmation is not None for row in active
        )
        shipment_scopes, line_ids = {}, set()
        assigned_shipments, assigned_lines = {}, set()
        for row in self.allocations:
            assignment = row.shipment_assignment
            if assignment is not None:
                scope = (
                    assignment.shipment_id,
                    assignment.shipment_version,
                    assignment.source_plan_version,
                    assignment.assigned_at,
                )
                shipment_scope = (row.source.warehouse_id, *scope[1:])
                key = (assignment.shipment_id, assignment.shipment_line_id)
                if (
                    assignment.assigned_at > self.updated_at
                    or assignment.source_plan_version >= self.version
                    or assigned_shipments.setdefault(
                        assignment.shipment_id, shipment_scope
                    )
                    != shipment_scope
                    or key in assigned_lines
                ):
                    raise InvalidFulfillmentPlanShipmentSnapshotError(
                        "Назначения одного Shipment должны относиться к одному складу, версии, времени и основанию с уникальными строками."
                    )
                assigned_lines.add(key)
            progress = row.shipment_progress
            if progress is None:
                continue
            checkpoint = (
                progress.shipment_id,
                progress.shipment_version,
                progress.shipment_updated_at,
                progress.source_plan_version,
            )
            scope = (row.source.warehouse_id, *checkpoint[1:])
            line_key = (progress.shipment_id, progress.shipment_line_id)
            if (
                progress.shipment_updated_at > self.updated_at
                or progress.source_plan_version >= self.version
                or shipment_scopes.setdefault(progress.shipment_id, scope) != scope
                or line_key in line_ids
            ):
                raise InvalidFulfillmentPlanShipmentSnapshotError(
                    "Контрольные точки каждой группы Shipment должны иметь один склад, версию, время и основание."
                )
            line_ids.add(line_key)
        if (
            not active
            or (
                self.status is FulfillmentPlanStatus.PARTIALLY_CONFIRMED
                and (
                    not confirmed
                    or confirmed == len(active)
                    or any_fulfilled
                    or bool(shipment_scopes)
                )
            )
            or (
                self.status is FulfillmentPlanStatus.CONFIRMED
                and (confirmed != len(active) or any_fulfilled or bool(shipment_scopes))
            )
            or (
                self.status is FulfillmentPlanStatus.PARTIALLY_FULFILLED
                and (not any_fulfilled or all_fulfilled)
            )
            or any(
                row.shipment_assignment is not None
                and row.shipment_assignment.shipment_id in shipment_scopes
                and row.shipment_progress is None
                for row in active
            )
        ):
            raise InvalidFulfillmentPlanShipmentSnapshotError(
                "Статус и полный состав контрольных точек не соответствуют накопленному исполнению."
            )
