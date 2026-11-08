from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.fulfillment_plan.supplier_dropship_option_snapshot import (
    SupplierDropshipOptionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderAssignmentSnapshot,
    SupplierOrderConfirmationSnapshot,
    SupplierOrderDraftLineSnapshot,
    SupplierOrderDraftSnapshot,
    SupplierOrderRejectionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_basis_snapshot import (
    SupplierOrderAllocationSnapshot,
    SupplierOrderBasisSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_shipment_snapshot import (
    SupplierOrderShipmentSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOrderIdVO,
)
from src.modules.inventory.domain.policy.fulfillment_replanning import (
    FulfillmentReplanningPolicy,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)

from src.modules.inventory.domain.policy.fulfillment_reservation_release import (
    FulfillmentReservationReleasePolicy,
)

from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_assignment import (
    FulfillmentShipmentAssignmentRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentShipmentAssignmentConflictError,
    FulfillmentSupplierOrderAssignmentError,
    FulfillmentSupplierOrderConfirmationError,
    FulfillmentSupplierOrderRejectionError,
    FulfillmentSupplierOrderShipmentError,
)
from src.modules.inventory.domain.policy.fulfillment_shipment_assignment import (
    FulfillmentShipmentAssignmentPolicy,
)
from src.modules.inventory.domain.shipment.assignment_snapshot import (
    ShipmentAssignmentSnapshot,
)

from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_progress_ref import (
    FulfillmentShipmentProgressRefVO,
)
from src.modules.inventory.domain.policy.fulfillment_shipment_progress import (
    FulfillmentShipmentProgressPolicy,
)
from src.modules.inventory.domain.shipment.fulfillment_snapshot import (
    ShipmentFulfillmentSnapshot,
)

from src.modules.inventory.domain.fulfillment_plan.shipment_snapshot import (
    FulfillmentAllocationShipmentSnapshot,
    FulfillmentPlanShipmentSnapshot,
)

from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_binding import (
    FulfillmentReservationBindingVO,
)
from src.modules.inventory.domain.policy.fulfillment_reservation import (
    FulfillmentReservationPolicy,
)
from src.modules.inventory.domain.stock_reservation.fulfillment_snapshot import (
    StockReservationFulfillmentSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentReservationConflictError,
)

from src.modules.inventory.domain.fulfillment_plan.demand_snapshot import (
    FulfillmentDemandSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    EmptyFulfillmentPlanError,
    FulfillmentAllocationConflictError,
    FulfillmentAllocationCancellationConflictError,
    FulfillmentAllocationNotFoundError,
    FulfillmentPlanContextError,
    FulfillmentPlanStatusError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentShipmentProgressMismatchError,
    InvalidFulfillmentAllocationError,
    InvalidFulfillmentPlanValueError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
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
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.fulfillment_plan import FulfillmentPlanPolicy
from src.modules.inventory.domain.policy.fulfillment_supplier_order_assignment import (
    FulfillmentSupplierOrderAssignmentPolicy,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot

_SUPPLIER_ORDER_PLAN_STATUSES = (
    FulfillmentPlanStatus.PLANNED,
    FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
    FulfillmentPlanStatus.PARTIALLY_FULFILLED,
)
_SUPPLIER_CONFIRMATION_PLAN_STATUSES = (
    *_SUPPLIER_ORDER_PLAN_STATUSES,
    FulfillmentPlanStatus.CONFIRMED,
)
_SUPPLIER_SHIPMENT_PLAN_STATUSES = (
    *_SUPPLIER_CONFIRMATION_PLAN_STATUSES,
    FulfillmentPlanStatus.FULFILLED,
    FulfillmentPlanStatus.AWAITING_ALLOCATION,
)


@dataclass(frozen=True, slots=True)
class FulfillmentPlan:
    """План одного заказа и владельца с распределениями и историческими подтверждениями без изменения чужих резервов и запасов."""

    id: FulfillmentPlanIdVO
    order_ref: FulfillmentOrderRefVO
    owner_id: StockOwnerIdVO
    status: FulfillmentPlanStatus
    allocations: tuple[FulfillmentAllocation, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: FulfillmentPlanIdVO,
        order_ref: FulfillmentOrderRefVO,
        owner_id: StockOwnerIdVO,
        created_at: datetime,
    ) -> Self:
        """Создаёт пустой DRAFT версии 0; принадлежность и потребность заказа проверяются при распределении."""
        return cls.restore(
            identifier=identifier,
            order_ref=order_ref,
            owner_id=owner_id,
            status=FulfillmentPlanStatus.DRAFT,
            allocations=(),
            created_at=created_at,
            updated_at=created_at,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FulfillmentPlanIdVO,
        order_ref: FulfillmentOrderRefVO,
        owner_id: StockOwnerIdVO,
        status: FulfillmentPlanStatus,
        allocations: tuple[FulfillmentAllocation, ...],
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает полный собственный состав без текущих заказа, товаров, складов и I/O."""
        plan = cls(
            identifier,
            order_ref,
            owner_id,
            status,
            allocations,
            cls._normalize_time(created_at),
            cls._normalize_time(updated_at),
            version,
        )
        plan._validate()
        return plan

    def add_allocation(
        self,
        allocation: FulfillmentAllocation,
        *,
        demand: FulfillmentDemandSnapshot,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Добавляет распределение черновика после проверки текущего товара/склада и всей потребности заказа."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if not isinstance(allocation, FulfillmentAllocation):
            raise InvalidFulfillmentAllocationError(
                "Нужна дочерняя Entity распределения."
            )
        allocation.ensure_compatible(inventory_item=inventory_item, warehouse=warehouse)
        candidate = self._changed(
            updated_at=normalized, allocations=(*self.allocations, allocation)
        )
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=self.order_ref, allocations=candidate.allocations, demand=demand
        )
        return candidate

    def change_allocation_quantity(
        self,
        *,
        identifier: FulfillmentAllocationIdVO,
        quantity: QuantityVO,
        demand: FulfillmentDemandSnapshot,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Меняет только количество черновика, сохраняя строку заказа, источник, товар и базовую единицу."""
        normalized = self._prepare_transition(expected_version, updated_at)
        original = self._find_allocation(identifier)
        if not isinstance(original.source, FulfillmentSourceRefVO):
            raise InvalidFulfillmentAllocationError(
                "Для прямой поставки используйте изменение количества с текущим предложением."
            )
        changed = FulfillmentAllocation.restore(
            identifier=original.id,
            source_ref=original.source_ref,
            inventory_item_id=original.inventory_item_id,
            base_uom=original.base_uom,
            source=original.source,
            quantity=quantity,
            status=original.status,
            reservation=original.reservation,
            fulfilled_qty=original.fulfilled_qty,
            shipment_progress=original.shipment_progress,
            shipment_assignment=original.shipment_assignment,
            reservation_releases=original.reservation_releases,
            cancelled_at=original.cancelled_at,
        )
        changed.ensure_compatible(inventory_item=inventory_item, warehouse=warehouse)
        candidate = self._changed(
            updated_at=normalized,
            allocations=tuple(
                changed if allocation.id == identifier else allocation
                for allocation in self.allocations
            ),
        )
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=self.order_ref, allocations=candidate.allocations, demand=demand
        )
        return candidate

    def add_supplier_allocation(
        self,
        *,
        identifier: FulfillmentAllocationIdVO,
        source_ref: ReservationSourceVO,
        quantity: QuantityVO,
        demand: FulfillmentDemandSnapshot,
        inventory_item: InventoryItemStockSnapshot,
        supplier_option: SupplierDropshipOptionSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Добавляет плановую прямую поставку из проверенного снимка предложения."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if not isinstance(supplier_option, SupplierDropshipOptionSnapshot):
            raise FulfillmentPlanContextError("Нужен снимок выбранной прямой поставки.")
        supplier_option.ensure_valid()
        allocation = FulfillmentAllocation.create(
            identifier=identifier,
            source_ref=source_ref,
            inventory_item=inventory_item,
            source=supplier_option.source,
            quantity=quantity,
            quoted_purchase_price=supplier_option.purchase_price,
        )
        allocation.ensure_supplier_compatible(
            inventory_item=inventory_item, option=supplier_option
        )
        candidate = self._changed(
            updated_at=normalized, allocations=(*self.allocations, allocation)
        )
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=self.order_ref, allocations=candidate.allocations, demand=demand
        )
        return candidate

    def change_supplier_allocation_quantity(
        self,
        *,
        identifier: FulfillmentAllocationIdVO,
        quantity: QuantityVO,
        demand: FulfillmentDemandSnapshot,
        inventory_item: InventoryItemStockSnapshot,
        supplier_option: SupplierDropshipOptionSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Меняет количество внешней строки черновика после повторной проверки предложения."""
        normalized = self._prepare_transition(expected_version, updated_at)
        original = self._find_allocation(identifier)
        if not isinstance(original.source, SupplierDropshipSourceRefVO):
            raise InvalidFulfillmentAllocationError(
                "Изменение по предложению поставщика требует внешнее распределение."
            )
        changed = replace(original, quantity=quantity)
        changed.ensure_supplier_compatible(
            inventory_item=inventory_item, option=supplier_option
        )
        candidate = self._changed(
            updated_at=normalized,
            allocations=tuple(
                changed if row.id == identifier else row for row in self.allocations
            ),
        )
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=self.order_ref, allocations=candidate.allocations, demand=demand
        )
        return candidate

    def remove_allocation(
        self,
        identifier: FulfillmentAllocationIdVO,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Удаляет распределение только из черновика без текущего заказа, склада и освобождения резерва."""
        normalized = self._prepare_transition(expected_version, updated_at)
        self._find_allocation(identifier)
        return self._changed(
            updated_at=normalized,
            allocations=tuple(
                allocation
                for allocation in self.allocations
                if allocation.id != identifier
            ),
        )

    def mark_planned(
        self,
        *,
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        expected_version: int,
        updated_at: datetime,
        supplier_options: tuple[SupplierDropshipOptionSnapshot, ...] = (),
    ) -> Self:
        """Фиксирует непустое проверенное намерение после повторной проверки всей потребности и текущих снимков."""
        normalized = self._prepare_transition(expected_version, updated_at)
        FulfillmentPlanPolicy.ensure_plannable(
            order_ref=self.order_ref,
            allocations=self.allocations,
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
            supplier_options=supplier_options,
        )
        return self._changed(
            updated_at=normalized, status=FulfillmentPlanStatus.PLANNED
        )

    def allocate_remaining_demand(
        self,
        *,
        allocations: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Дополняет действующий план свежими намерениями одной версией без изменения прежних подтверждений и исполнения."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PLANNED,
                FulfillmentPlanStatus.AWAITING_ALLOCATION,
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
                FulfillmentPlanStatus.FULFILLED,
            ),
        )
        if self.status is FulfillmentPlanStatus.FULFILLED and not any(
            row.supplier_rejection is not None
            or (
                row.supplier_confirmed_qty is not None
                and row.supplier_confirmed_qty.value < row.quantity.value
            )
            for row in self.allocations
        ):
            raise FulfillmentPlanStatusError(
                "Допланирование исполненного состава требует отказ или частичное подтверждение поставщика."
            )
        FulfillmentPlanPolicy.ensure_extendable(
            order_ref=self.order_ref,
            existing_allocations=self.allocations,
            allocations=allocations,
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
        )
        candidate = (*self.allocations, *allocations)
        return self._changed(
            updated_at=normalized,
            allocations=candidate,
            status=self._status_from_allocations(candidate),
        )

    def replan_allocations(
        self,
        *,
        allocation_ids: tuple[FulfillmentAllocationIdVO, ...],
        replacements: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Заменяет выбранные не начатые намерения одной версией, сохраняя их терминальную историю и другие обязательства."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PLANNED,
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            ),
        )
        allocations = FulfillmentReplanningPolicy.build_allocations(
            order_ref=self.order_ref,
            allocations=self.allocations,
            allocation_ids=allocation_ids,
            replacements=replacements,
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
            as_of=normalized,
        )
        return self._changed(
            updated_at=normalized,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    def confirm_reservations(
        self,
        *,
        bindings: tuple[FulfillmentReservationBindingVO, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Закрепляет новые полные удержания, проверяя оставшийся спрос и прежние ещё не начатые резервы."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PLANNED,
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            ),
        )
        FulfillmentPlanPolicy.ensure_confirmable_reservations(
            order_ref=self.order_ref,
            allocations=self.allocations,
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
        )
        confirmations = FulfillmentReservationPolicy.build_confirmations(
            owner_id=self.owner_id,
            allocations=self.allocations,
            bindings=bindings,
            reservations=reservations,
            as_of=normalized,
        )
        allocations = tuple(
            (
                allocation.confirm_reservation(confirmations[allocation.id])
                if allocation.id in confirmations
                else allocation
            )
            for allocation in self.allocations
        )
        return self._changed(
            updated_at=normalized,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    def release_reservation_confirmations(
        self,
        *,
        bindings: tuple[FulfillmentReservationBindingVO, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Снимает выбранные подтверждения по закрытым резервам одной версией с сохранением истории и прогресса остальных строк."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PLANNED,
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            ),
        )
        releases = FulfillmentReservationReleasePolicy.build_releases(
            owner_id=self.owner_id,
            allocations=self.allocations,
            bindings=bindings,
            reservations=reservations,
            as_of=normalized,
        )
        allocations = tuple(
            (
                row.release_reservation_confirmation(releases[row.id])
                if row.id in releases
                else row
            )
            for row in self.allocations
        )
        return self._changed(
            updated_at=normalized,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    def assign_shipment(
        self,
        shipment: ShipmentAssignmentSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Назначает выбранную группу производному черновику одной версией без исполнения или изменения резервов."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            ),
        )
        FulfillmentShipmentAssignmentPolicy.ensure_assignable(
            plan_id=self.id,
            plan_version=self.version,
            order_ref=self.order_ref,
            owner_id=self.owner_id,
            allocations=self.allocations,
            shipment=shipment,
            as_of=normalized,
        )
        by_id = {row.fulfillment_allocation_id: row for row in shipment.lines}
        allocations = tuple(
            (
                row.assign_shipment(
                    FulfillmentShipmentAssignmentRefVO(
                        shipment.id,
                        by_id[row.id].id,
                        shipment.version,
                        shipment.fulfillment_source.plan_version,
                        normalized,
                    )
                )
                if row.id in by_id
                else row
            )
            for row in self.allocations
        )
        return self._changed(updated_at=normalized, allocations=allocations)

    def release_shipment_assignment(
        self,
        shipment: ShipmentAssignmentSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Снимает назначение отменённого черновика до исполнения, сохраняя резервные подтверждения и количества."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            ),
        )
        FulfillmentShipmentAssignmentPolicy.ensure_releasable(
            plan_id=self.id,
            plan_version=self.version,
            order_ref=self.order_ref,
            owner_id=self.owner_id,
            allocations=self.allocations,
            shipment=shipment,
            as_of=normalized,
        )
        ids = {row.fulfillment_allocation_id for row in shipment.lines}
        return self._changed(
            updated_at=normalized,
            allocations=tuple(
                row.release_shipment_assignment() if row.id in ids else row
                for row in self.allocations
            ),
        )

    def register_shipment(
        self,
        shipment: ShipmentFulfillmentSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Регистрирует весь накопленный прогресс одного Shipment одной версией либо возвращает прежний объект при точном повторе."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
                FulfillmentPlanStatus.FULFILLED,
            ),
        )
        FulfillmentShipmentProgressPolicy.ensure_compatible(
            plan_id=self.id,
            plan_version=self.version,
            plan_status=self.status,
            order_ref=self.order_ref,
            owner_id=self.owner_id,
            allocations=self.allocations,
            shipment=shipment,
            as_of=normalized,
        )
        by_id = {line.fulfillment_allocation_id: line for line in shipment.lines}
        allocations = tuple(
            (
                allocation.register_shipment_progress(
                    fulfilled_qty=by_id[allocation.id].shipped_qty,
                    progress=FulfillmentShipmentProgressRefVO(
                        shipment.id,
                        by_id[allocation.id].id,
                        shipment.version,
                        shipment.updated_at,
                        shipment.fulfillment_source.plan_version,
                    ),
                )
                if allocation.id in by_id
                else allocation
            )
            for allocation in self.allocations
        )
        return self._changed(
            updated_at=normalized,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    def supplier_order_basis_snapshot(
        self, *, allocation_ids: tuple[FulfillmentAllocationIdVO, ...]
    ) -> SupplierOrderBasisSnapshot:
        """Экспортирует явно выбранные плановые прямые поставки для черновика поставщику."""
        self._validate()
        if self.status not in _SUPPLIER_ORDER_PLAN_STATUSES:
            raise FulfillmentPlanStatusError(
                "Внешний заказ требует зафиксированный план с ещё не исполненными прямыми поставками."
            )
        if not isinstance(allocation_ids, tuple) or not allocation_ids:
            raise FulfillmentPlanContextError(
                "Нужен непустой tuple выбранных ID внешних распределений."
            )
        rows = []
        for identifier in allocation_ids:
            row = self._find_allocation(identifier)
            if row.supplier_order_assignment is not None:
                raise FulfillmentPlanContextError(
                    "Распределение уже закреплено за внешним заказом."
                )
            rows.append(self._supplier_order_allocation_snapshot(row))
        snapshot = SupplierOrderBasisSnapshot(
            self.id, self.version, self.updated_at, tuple(rows)
        )
        snapshot.ensure_valid()
        return snapshot

    def assign_supplier_order(
        self,
        draft: SupplierOrderDraftSnapshot,
        *,
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        supplier_options: tuple[SupplierDropshipOptionSnapshot, ...],
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Закрепляет весь черновик поставщику одной версией плана после проверки условий."""
        normalized = self._prepare_transition(
            expected_version, updated_at, allowed_statuses=_SUPPLIER_ORDER_PLAN_STATUSES
        )
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=self.order_ref, allocations=self.allocations, demand=demand
        )
        assignments = FulfillmentSupplierOrderAssignmentPolicy.build_assignments(
            plan_id=self.id,
            plan_version=self.version,
            allocations=self.allocations,
            draft=draft,
            inventory_items=inventory_items,
            supplier_options=supplier_options,
            as_of=normalized,
        )
        allocations = tuple(
            (
                row.assign_supplier_order(assignments[row.id])
                if row.id in assignments
                else row
            )
            for row in self.allocations
        )
        if allocations == self.allocations:
            return self
        return self._changed(updated_at=normalized, allocations=allocations)

    def register_supplier_confirmation(
        self,
        snapshot: SupplierOrderConfirmationSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Регистрирует полный или частичный ответ по всей закреплённой группе."""
        at = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=_SUPPLIER_SHIPMENT_PLAN_STATUSES,
        )
        if not isinstance(snapshot, SupplierOrderConfirmationSnapshot):
            raise FulfillmentSupplierOrderConfirmationError(
                "Нужен специализированный снимок подтверждения поставщика."
            )
        snapshot.ensure_valid()
        quantities = self._supplier_confirmation_quantities(snapshot, as_of=at)
        allocations = tuple(
            (
                row.confirm_supplier_order(snapshot.confirmation, quantities[row.id])
                if row.id in quantities
                else row
            )
            for row in self.allocations
        )
        if allocations == self.allocations:
            return self
        return self._changed(
            updated_at=at,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    def _supplier_confirmation_quantities(
        self, snapshot: SupplierOrderConfirmationSnapshot, *, as_of: datetime
    ) -> dict[FulfillmentAllocationIdVO, QuantityVO]:
        """Сверяет историческое основание подтверждения с полным закреплением плана."""
        try:
            assignment = self.supplier_order_assignment_snapshot(
                order_id=snapshot.order_id
            )
        except FulfillmentSupplierOrderAssignmentError as exc:
            raise FulfillmentSupplierOrderConfirmationError(
                "Подтверждение требует закреплённый внешний заказ."
            ) from exc
        confirmation = snapshot.confirmation
        if (
            snapshot.plan_id != self.id
            or snapshot.supplier_id != assignment.supplier_id
            or snapshot.source_plan_version != assignment.source_plan_version
            or confirmation.order_version != assignment.order_version + 2
            or set(snapshot.lines) != set(assignment.lines)
        ):
            raise FulfillmentSupplierOrderConfirmationError(
                "Ответ должен подтверждать полный состав и условия закреплённого заказа."
            )
        if (
            confirmation.requested_at < assignment.assigned_at
            or confirmation.confirmed_at > as_of
        ):
            raise FulfillmentPlanTimeError(
                "Запрос следует за закреплением, а подтверждение предшествует регистрации в плане."
            )
        if snapshot.confirmed_quantities is None:
            if assignment.quantity_terms:
                raise FulfillmentSupplierOrderConfirmationError(
                    "Для заказа с сохранёнными правилами нужны количества ответа."
                )
            by_line = {
                line.line_id: line.allocation.quantity for line in snapshot.lines
            }
        else:
            by_line = dict(snapshot.confirmed_quantities)
        return {line.allocation.id: by_line[line.line_id] for line in assignment.lines}

    def register_supplier_shipment(
        self,
        snapshot: SupplierOrderShipmentSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Регистрирует один факт исполнения всего подтверждённого заказа поставщику."""
        at = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=_SUPPLIER_SHIPMENT_PLAN_STATUSES,
        )
        if not isinstance(snapshot, SupplierOrderShipmentSnapshot):
            raise FulfillmentSupplierOrderShipmentError(
                "Нужен специализированный снимок внешней отправки."
            )
        snapshot.ensure_valid()
        if snapshot.shipment.shipped_at > at:
            raise FulfillmentPlanTimeError(
                "Регистрация в плане не может предшествовать внешней отправке."
            )
        try:
            quantities = self._supplier_confirmation_quantities(
                snapshot.confirmation, as_of=at
            )
        except FulfillmentSupplierOrderConfirmationError as exc:
            raise FulfillmentSupplierOrderShipmentError(
                "Отправка требует совпадающее основание закреплённого заказа."
            ) from exc
        for row in self.allocations:
            if row.id in quantities and (
                row.supplier_confirmation != snapshot.confirmation.confirmation
                or row.quantity_to_fulfill() != quantities[row.id]
            ):
                raise FulfillmentSupplierOrderShipmentError(
                    "План должен содержать зарегистрированное подтверждение всех строк отправки."
                )
        allocations = tuple(
            (
                row.register_supplier_shipment(snapshot.shipment, quantities[row.id])
                if row.id in quantities and not quantities[row.id].value.is_zero()
                else row
            )
            for row in self.allocations
        )
        if allocations == self.allocations:
            return self
        return self._changed(
            updated_at=at,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    def register_supplier_rejection(
        self,
        snapshot: SupplierOrderRejectionSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Закрывает всю закреплённую группу по явному отказу и освобождает её спрос."""
        at = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                *_SUPPLIER_CONFIRMATION_PLAN_STATUSES,
                FulfillmentPlanStatus.AWAITING_ALLOCATION,
                FulfillmentPlanStatus.FULFILLED,
                FulfillmentPlanStatus.CANCELLED,
            ),
        )
        if not isinstance(snapshot, SupplierOrderRejectionSnapshot):
            raise FulfillmentSupplierOrderRejectionError(
                "Нужен специализированный снимок отказа поставщика."
            )
        snapshot.ensure_valid()
        try:
            assignment = self.supplier_order_assignment_snapshot(
                order_id=snapshot.order_id
            )
        except FulfillmentSupplierOrderAssignmentError as exc:
            raise FulfillmentSupplierOrderRejectionError(
                "Отказ требует закреплённый внешний заказ."
            ) from exc
        rejection = snapshot.rejection
        if (
            snapshot.plan_id != self.id
            or snapshot.supplier_id != assignment.supplier_id
            or snapshot.source_plan_version != assignment.source_plan_version
            or rejection.order_version != assignment.order_version + 2
            or set(snapshot.lines) != set(assignment.lines)
        ):
            raise FulfillmentSupplierOrderRejectionError(
                "Отказ должен соответствовать всем закреплённым строкам заказа."
            )
        if (
            rejection.requested_at < assignment.assigned_at
            or rejection.rejected_at > at
        ):
            raise FulfillmentPlanTimeError(
                "Запрос следует за закреплением, а отказ предшествует регистрации в плане."
            )
        selected = {line.allocation.id for line in assignment.lines}
        allocations = tuple(
            row.reject_supplier_order(rejection) if row.id in selected else row
            for row in self.allocations
        )
        if allocations == self.allocations:
            return self
        status = self._status_from_allocations(allocations)
        if status in (FulfillmentPlanStatus.CANCELLED, FulfillmentPlanStatus.FULFILLED):
            status = FulfillmentPlanStatus.AWAITING_ALLOCATION
        return self._changed(updated_at=at, allocations=allocations, status=status)

    def supplier_order_assignment_snapshot(
        self, *, order_id: FulfillmentSupplierOrderIdVO
    ) -> SupplierOrderAssignmentSnapshot:
        """Экспортирует все строки, закреплённые за указанным внешним заказом."""
        self._validate()
        if not isinstance(order_id, FulfillmentSupplierOrderIdVO):
            raise FulfillmentSupplierOrderAssignmentError("Нужен ID внешнего заказа.")
        lines = []
        quantity_terms = []
        assignment = None
        for row in self.allocations:
            current = row.supplier_order_assignment
            if current is not None and current.order_id == order_id:
                assignment = current
                lines.append(
                    SupplierOrderDraftLineSnapshot(
                        current.line_id, self._supplier_order_allocation_snapshot(row)
                    )
                )
                if current.quantity_terms is not None:
                    quantity_terms.append((current.line_id, current.quantity_terms))
        if assignment is None:
            raise FulfillmentSupplierOrderAssignmentError(
                "Заказ не закреплён в этом плане."
            )
        snapshot = SupplierOrderAssignmentSnapshot(
            self.id,
            self.version,
            self.updated_at,
            assignment.order_id,
            assignment.order_version,
            assignment.supplier_id,
            assignment.source_plan_version,
            assignment.assigned_at,
            tuple(lines),
            tuple(quantity_terms),
        )
        snapshot.ensure_valid()
        return snapshot

    @staticmethod
    def _supplier_order_allocation_snapshot(
        row: FulfillmentAllocation,
    ) -> SupplierOrderAllocationSnapshot:
        """Проецирует исходные условия прямой поставки, включая нулевой ответ."""
        if (
            not isinstance(row.source, SupplierDropshipSourceRefVO)
            or (
                row.status is not FulfillmentAllocationStatus.PLANNED
                and row.supplier_confirmation is None
                and row.supplier_rejection is None
            )
            or row.quoted_purchase_price is None
        ):
            raise FulfillmentPlanContextError(
                "Для внешнего заказа выбираются целые плановые распределения прямой поставки."
            )
        return SupplierOrderAllocationSnapshot(
            row.id,
            row.source,
            row.inventory_item_id,
            row.base_uom,
            row.quantity,
            row.quoted_purchase_price,
        )

    def shipment_snapshot(self) -> FulfillmentPlanShipmentSnapshot:
        """Передаёт все распределения плана с подтверждениями и прогрессом для выбора готового ещё не начатого склада."""
        self._validate()
        if self.status not in (
            FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
            FulfillmentPlanStatus.CONFIRMED,
            FulfillmentPlanStatus.PARTIALLY_FULFILLED,
        ):
            raise FulfillmentPlanStatusError(
                "Построение Shipment требует план с подтверждениями и готовыми ещё не начатыми Allocation."
            )
        snapshot = FulfillmentPlanShipmentSnapshot(
            self.id,
            self.version,
            self.status,
            self.order_ref,
            self.owner_id,
            self.updated_at,
            tuple(
                FulfillmentAllocationShipmentSnapshot(
                    allocation.id,
                    allocation.source_ref,
                    allocation.inventory_item_id,
                    allocation.base_uom,
                    allocation.source,
                    allocation.quantity,
                    allocation.reservation,
                    allocation.status,
                    allocation.fulfilled_qty,
                    allocation.shipment_progress,
                    allocation.shipment_assignment,
                    allocation.reservation_releases,
                    allocation.cancelled_at,
                    allocation.quoted_purchase_price,
                    allocation.supplier_order_assignment,
                    allocation.supplier_confirmation,
                    allocation.supplier_confirmed_qty,
                    allocation.supplier_rejection,
                    allocation.supplier_shipment,
                )
                for allocation in self.allocations
            ),
        )
        snapshot.ensure_valid()
        return snapshot

    def cancel_allocations(
        self,
        *,
        allocation_ids: tuple[FulfillmentAllocationIdVO, ...],
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Отменяет выбранные не начатые намерения без замены одной версией либо сохраняет корень при повторе."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.PLANNED,
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.FULFILLED,
                FulfillmentPlanStatus.CANCELLED,
            ),
        )
        if not isinstance(allocation_ids, tuple) or not allocation_ids:
            raise FulfillmentAllocationCancellationConflictError(
                "Нужен непустой tuple уникальных ID отменяемых распределений."
            )
        selected = set()
        for identifier in allocation_ids:
            row = self._find_allocation(identifier)
            if identifier in selected:
                raise FulfillmentAllocationCancellationConflictError(
                    "ID в пакете отмены не должен повторяться."
                )
            if (
                self.status
                in (
                    FulfillmentPlanStatus.CONFIRMED,
                    FulfillmentPlanStatus.FULFILLED,
                    FulfillmentPlanStatus.CANCELLED,
                )
                and row.status is not FulfillmentAllocationStatus.CANCELLED
            ):
                raise FulfillmentPlanStatusError(
                    "Это состояние плана допускает только повтор отмены исторических строк."
                )
            selected.add(identifier)
        allocations = tuple(
            row.cancel_unstarted(cancelled_at=normalized) if row.id in selected else row
            for row in self.allocations
        )
        if allocations == self.allocations:
            return self
        return self._changed(
            updated_at=normalized,
            allocations=allocations,
            status=self._status_from_allocations(allocations),
        )

    @staticmethod
    def _status_from_allocations(
        allocations: tuple[FulfillmentAllocation, ...],
    ) -> FulfillmentPlanStatus:
        """Определяет состояние действующего плана по исполнению и обоим видам подтверждения."""
        active = tuple(
            row
            for row in allocations
            if row.status is not FulfillmentAllocationStatus.CANCELLED
        )
        if not active:
            return FulfillmentPlanStatus.CANCELLED
        if all(row.fulfilled_qty == row.quantity_to_fulfill() for row in active):
            return FulfillmentPlanStatus.FULFILLED
        if any(not row.fulfilled_qty.value.is_zero() for row in active):
            return FulfillmentPlanStatus.PARTIALLY_FULFILLED
        if all(row.is_confirmed() for row in active):
            return FulfillmentPlanStatus.CONFIRMED
        if any(row.is_confirmed() for row in active):
            return FulfillmentPlanStatus.PARTIALLY_CONFIRMED
        return FulfillmentPlanStatus.PLANNED

    def cancel(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Отменяет DRAFT или PLANNED с сохранением распределений, пока внешние обязательства не создаются."""
        normalized = self._prepare_transition(
            expected_version,
            updated_at,
            allowed_statuses=(
                FulfillmentPlanStatus.DRAFT,
                FulfillmentPlanStatus.PLANNED,
            ),
        )
        return self._changed(
            updated_at=normalized, status=FulfillmentPlanStatus.CANCELLED
        )

    def is_fully_confirmed(self) -> bool:
        """Проверяет историческое подтверждение всех распределений без переоценки текущих удержаний."""
        self._validate()
        active = self._active_allocations()
        return bool(active) and all(row.is_confirmed() for row in active)

    def get_allocation(
        self, identifier: FulfillmentAllocationIdVO
    ) -> FulfillmentAllocation:
        """Возвращает собственную неизменяемую Entity, в том числе для чтения отменённой истории."""
        self._validate()
        return self._find_allocation(identifier)

    def remaining_to_allocate(
        self, source_ref: ReservationSourceVO, *, demand: FulfillmentDemandSnapshot
    ) -> QuantityVO:
        """Точно вычисляет остаток активного плана по текущей потребности, отклоняя устаревшее превышение лимитов."""
        self._validate()
        if self.status is FulfillmentPlanStatus.CANCELLED:
            raise FulfillmentPlanStatusError(
                "Отменённый план не имеет активного остатка к распределению."
            )
        if not isinstance(source_ref, ReservationSourceVO):
            raise FulfillmentPlanContextError(
                "Нужна типизированная ссылка строки заказа."
            )
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=self.order_ref, allocations=self.allocations, demand=demand
        )
        line = next(
            (line for line in demand.lines if line.source_ref == source_ref), None
        )
        if line is None:
            raise FulfillmentPlanContextError(
                "Строка отсутствует в потребности данного заказа."
            )
        allocated = QuantityVO(Decimal(0))
        for allocation in self.allocations:
            if allocation.source_ref == source_ref:
                allocated = QuantityArithmeticPolicy.add(
                    allocated, allocation.remaining_to_fulfill()
                )
        return QuantityArithmeticPolicy.subtract(line.remaining_qty, allocated)

    def _prepare_transition(
        self,
        expected_version: int,
        updated_at: datetime,
        *,
        allowed_statuses: tuple[FulfillmentPlanStatus, ...] = (
            FulfillmentPlanStatus.DRAFT,
        ),
    ) -> datetime:
        """Проверяет строгую версию до арифметики, собственный состав, разрешённое состояние и неубывание времени."""
        if (
            type(self.version) is not int
            or self.version < 0
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise InvalidFulfillmentPlanValueError(
                "Версии должны быть целыми неотрицательными без bool."
            )
        if expected_version != self.version:
            raise FulfillmentPlanVersionConflictError(
                "Ожидаемая версия плана устарела."
            )
        self._validate()
        if self.status not in allowed_statuses:
            raise FulfillmentPlanStatusError(
                "Состояние плана не допускает эту операцию."
            )
        normalized = self._normalize_time(updated_at)
        if normalized < self.updated_at:
            raise FulfillmentPlanTimeError("Время изменения плана не может убывать.")
        return normalized

    def _active_allocations(self) -> tuple[FulfillmentAllocation, ...]:
        """Выбирает действующий состав из уже проверенных дочерних строк, сохраняя историю отдельно от расчётов."""
        return tuple(
            row
            for row in self.allocations
            if row.status is not FulfillmentAllocationStatus.CANCELLED
        )

    def _find_allocation(
        self, identifier: FulfillmentAllocationIdVO
    ) -> FulfillmentAllocation:
        """Находит дочернее распределение без отдельного write repository."""
        if not isinstance(identifier, FulfillmentAllocationIdVO):
            raise InvalidFulfillmentAllocationError(
                "Нужен типизированный ID распределения."
            )
        for allocation in self.allocations:
            if allocation.id == identifier:
                return allocation
        raise FulfillmentAllocationNotFoundError(
            "Распределение отсутствует в данном плане."
        )

    def _changed(self, *, updated_at: datetime, **changes: object) -> Self:
        """Возвращает новый проверенный экземпляр версии +1 либо прежний объект при численно равном содержимом."""
        candidate = replace(self, **changes)
        if candidate == self:
            candidate._validate()
            return self
        candidate = replace(candidate, updated_at=updated_at, version=self.version + 1)
        candidate._validate()
        return candidate

    def _validate(self) -> None:
        """Проверяет собственные типы, UTC-хронологию, уникальность источников и единую идентичность каждой строки заказа."""
        if (
            not isinstance(self.id, FulfillmentPlanIdVO)
            or not isinstance(self.order_ref, FulfillmentOrderRefVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.status, FulfillmentPlanStatus)
            or not isinstance(self.allocations, tuple)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidFulfillmentPlanValueError(
                "Нужны типизированные поля плана, tuple распределений и целая неотрицательная версия без bool."
            )
        created, updated = self._normalize_time(self.created_at), self._normalize_time(
            self.updated_at
        )
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or updated < created
        ):
            raise FulfillmentPlanTimeError(
                "Сохранённые даты должны быть в UTC; изменение не раньше создания."
            )
        ids, pairs, identities, reservations = set(), set(), {}, set()
        confirmed = 0
        historical_reservations = set()
        shipment_scopes, shipment_lines = {}, set()
        assigned_shipments, assigned_lines = {}, set()
        supplier_orders, supplier_lines = {}, set()
        supplier_shipments, supplier_shipment_orders = {}, {}
        responded_orders, accepted_orders = set(), set()
        has_supplier_rejection = False
        for allocation in self.allocations:
            if not isinstance(allocation, FulfillmentAllocation):
                raise InvalidFulfillmentAllocationError(
                    "Состав плана содержит только FulfillmentAllocation."
                )
            allocation.ensure_valid()
            supplier_assignment = allocation.supplier_order_assignment
            supplier_confirmation = allocation.supplier_confirmation
            supplier_rejection = allocation.supplier_rejection
            if supplier_assignment is not None:
                group = (
                    allocation.source.supplier_source_id,
                    supplier_assignment.supplier_id,
                    supplier_assignment.order_version,
                    supplier_assignment.source_plan_version,
                    supplier_assignment.assigned_at,
                    supplier_assignment.quantity_terms is not None,
                    supplier_confirmation,
                    supplier_rejection,
                )
                key = (supplier_assignment.order_id, supplier_assignment.line_id)
                if (
                    (
                        supplier_rejection is None
                        and self.status not in _SUPPLIER_SHIPMENT_PLAN_STATUSES
                    )
                    or not created <= supplier_assignment.assigned_at <= updated
                    or supplier_assignment.source_plan_version >= self.version
                    or supplier_orders.setdefault(supplier_assignment.order_id, group)
                    != group
                    or key in supplier_lines
                ):
                    raise FulfillmentSupplierOrderAssignmentError(
                        "Закрепление требует действующий план, согласованную группу и уникальные строки внешнего заказа."
                    )
                supplier_lines.add(key)
                if supplier_confirmation is not None:
                    responded_orders.add(supplier_assignment.order_id)
                    if allocation.is_confirmed():
                        accepted_orders.add(supplier_assignment.order_id)
                        shipment = allocation.supplier_shipment
                        if supplier_shipments.setdefault(
                            supplier_assignment.order_id, shipment
                        ) != shipment or (
                            shipment is not None
                            and (
                                shipment.shipped_at > updated
                                or supplier_shipment_orders.setdefault(
                                    shipment.shipment_id, supplier_assignment.order_id
                                )
                                != supplier_assignment.order_id
                            )
                        ):
                            raise FulfillmentSupplierOrderShipmentError(
                                "Все подтверждённые строки заказа требуют один согласованный факт отправки."
                            )
            if (
                supplier_confirmation is not None
                and supplier_confirmation.confirmed_at > updated
            ):
                raise FulfillmentPlanTimeError(
                    "Подтверждение поставщика должно находиться внутри истории плана."
                )
            if supplier_rejection is not None:
                if supplier_rejection.rejected_at > updated:
                    raise FulfillmentPlanTimeError(
                        "Отказ поставщика должен находиться внутри истории плана."
                    )
                has_supplier_rejection = True
            if allocation.is_confirmed():
                confirmed += 1
            pair = (allocation.source_ref, allocation.source)
            identity = (allocation.inventory_item_id, allocation.base_uom)
            if (
                allocation.id in ids
                or (
                    allocation.status is not FulfillmentAllocationStatus.CANCELLED
                    and pair in pairs
                )
                or (
                    allocation.source_ref in identities
                    and identities[allocation.source_ref] != identity
                )
            ):
                raise FulfillmentAllocationConflictError(
                    "ID, пара строка/источник повторяются либо одна строка имеет разные товар/базовую единицу."
                )
            ids.add(allocation.id)
            if allocation.status is not FulfillmentAllocationStatus.CANCELLED:
                pairs.add(pair)
            elif not created <= allocation.cancelled_at <= updated:
                raise FulfillmentPlanTimeError(
                    "Отмена распределения должна находиться внутри истории плана."
                )
            identities[allocation.source_ref] = identity
            if allocation.reservation is not None:
                ref = allocation.reservation
                if (
                    ref.reservation_id in reservations
                    or ref.reservation_id in historical_reservations
                ):
                    raise FulfillmentReservationConflictError(
                        "Один резерв не может подтверждать несколько распределений плана."
                    )
                if not created <= ref.confirmed_at <= updated:
                    raise FulfillmentPlanTimeError(
                        "Подтверждение распределения должно находиться между созданием и последним изменением плана."
                    )
                reservations.add(ref.reservation_id)
            for release in allocation.reservation_releases:
                identifier = release.confirmation.reservation_id
                if identifier in reservations or identifier in historical_reservations:
                    raise FulfillmentReservationConflictError(
                        "Снятый резервный ID остаётся уникальным во всём плане."
                    )
                if (
                    not created
                    <= release.confirmation.confirmed_at
                    <= release.closed_at
                    <= release.released_at
                    <= updated
                ):
                    raise FulfillmentPlanTimeError(
                        "История снятия должна находиться внутри хронологии плана."
                    )
                historical_reservations.add(identifier)
            assignment = allocation.shipment_assignment
            if assignment is not None:
                scope = (
                    assignment.shipment_id,
                    assignment.shipment_version,
                    assignment.source_plan_version,
                    assignment.assigned_at,
                )
                shipment_scope = (allocation.source.warehouse_id, *scope[1:])
                key = (assignment.shipment_id, assignment.shipment_line_id)
                if (
                    not created <= assignment.assigned_at <= updated
                    or assignment.source_plan_version >= self.version
                    or assigned_shipments.setdefault(
                        assignment.shipment_id, shipment_scope
                    )
                    != shipment_scope
                    or key in assigned_lines
                ):
                    raise FulfillmentShipmentAssignmentConflictError(
                        "Один Shipment должен иметь согласованное назначение на один склад уникальными строками, внутри истории плана."
                    )
                assigned_lines.add(key)
            progress = allocation.shipment_progress
            if progress is not None:
                if (
                    not created <= progress.shipment_updated_at <= updated
                    or progress.source_plan_version >= self.version
                ):
                    raise FulfillmentPlanTimeError(
                        "Контрольная точка должна быть внутри истории плана с более ранней версией основания."
                    )
                warehouse_id = allocation.source.warehouse_id
                shipment_scope = (
                    warehouse_id,
                    progress.shipment_version,
                    progress.shipment_updated_at,
                    progress.source_plan_version,
                )
                pair = (progress.shipment_id, progress.shipment_line_id)
                if (
                    shipment_scopes.setdefault(progress.shipment_id, shipment_scope)
                    != shipment_scope
                    or pair in shipment_lines
                ):
                    raise FulfillmentShipmentProgressMismatchError(
                        "Все Allocation одного Shipment должны иметь одну версию/время/основание прогресса и уникальные строки."
                    )
                shipment_lines.add(pair)
        if responded_orders != accepted_orders:
            raise FulfillmentSupplierOrderConfirmationError(
                "Ответ по группе внешнего заказа требует положительное подтверждение."
            )
        active = self._active_allocations()
        any_fulfilled = any(
            not allocation.fulfilled_qty.value.is_zero()
            for allocation in self.allocations
        )
        all_fulfilled = bool(active) and all(
            allocation.fulfilled_qty == allocation.quantity_to_fulfill()
            for allocation in active
        )
        if any(
            row.shipment_assignment is not None
            and row.shipment_assignment.shipment_id in shipment_scopes
            and row.shipment_progress is None
            for row in active
        ):
            raise FulfillmentShipmentProgressMismatchError(
                "Контрольная точка должна включать все Allocation группы Shipment, включая строки без отгрузки."
            )
        if (
            self.status
            not in (
                FulfillmentPlanStatus.DRAFT,
                FulfillmentPlanStatus.CANCELLED,
                FulfillmentPlanStatus.AWAITING_ALLOCATION,
            )
            and not active
        ):
            raise EmptyFulfillmentPlanError(
                "Зафиксированный план не может быть пустым."
            )
        if (
            (
                self.status is FulfillmentPlanStatus.DRAFT
                and (
                    bool(historical_reservations)
                    or len(active) != len(self.allocations)
                )
            )
            or (
                self.status
                in (
                    FulfillmentPlanStatus.DRAFT,
                    FulfillmentPlanStatus.PLANNED,
                    FulfillmentPlanStatus.CANCELLED,
                )
                and confirmed != 0
            )
            or (
                self.status is FulfillmentPlanStatus.PARTIALLY_CONFIRMED
                and (confirmed == 0 or confirmed == len(active))
            )
            or (
                self.status
                in (
                    FulfillmentPlanStatus.CONFIRMED,
                    FulfillmentPlanStatus.FULFILLED,
                )
                and confirmed != len(active)
            )
            or (
                self.status
                not in (
                    FulfillmentPlanStatus.AWAITING_ALLOCATION,
                    FulfillmentPlanStatus.PARTIALLY_FULFILLED,
                    FulfillmentPlanStatus.FULFILLED,
                )
                and (any_fulfilled or bool(shipment_lines))
            )
            or (
                self.status is FulfillmentPlanStatus.PARTIALLY_FULFILLED
                and (not any_fulfilled or all_fulfilled)
            )
            or (self.status is FulfillmentPlanStatus.FULFILLED and not all_fulfilled)
            or (
                self.status is FulfillmentPlanStatus.AWAITING_ALLOCATION
                and (not has_supplier_rejection or (bool(active) and not all_fulfilled))
            )
        ):
            raise InvalidFulfillmentPlanValueError(
                "Статус плана не соответствует подтверждениям и накопленному исполнению распределений."
            )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Нормализует явно переданное время в UTC без чтения часов или внешней инфраструктуры."""
        return normalize_fulfillment_time(value)
