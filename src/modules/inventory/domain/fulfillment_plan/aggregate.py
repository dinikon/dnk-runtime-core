from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Self

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
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


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
    ) -> Self:
        """Фиксирует непустое проверенное намерение после повторной проверки всей потребности и текущих снимков."""
        normalized = self._prepare_transition(expected_version, updated_at)
        FulfillmentPlanPolicy.ensure_plannable(
            order_ref=self.order_ref,
            allocations=self.allocations,
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
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
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED,
                FulfillmentPlanStatus.CONFIRMED,
                FulfillmentPlanStatus.PARTIALLY_FULFILLED,
            ),
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
        if any(not row.fulfilled_qty.value.is_zero() for row in candidate):
            status = FulfillmentPlanStatus.PARTIALLY_FULFILLED
        elif any(row.reservation is not None for row in candidate):
            status = FulfillmentPlanStatus.PARTIALLY_CONFIRMED
        else:
            status = FulfillmentPlanStatus.PLANNED
        return self._changed(
            updated_at=normalized, allocations=candidate, status=status
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
        status = (
            FulfillmentPlanStatus.PARTIALLY_FULFILLED
            if any(not row.fulfilled_qty.value.is_zero() for row in allocations)
            else (
                FulfillmentPlanStatus.PARTIALLY_CONFIRMED
                if any(row.reservation is not None for row in allocations)
                else FulfillmentPlanStatus.PLANNED
            )
        )
        return self._changed(
            updated_at=normalized, allocations=allocations, status=status
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
        status = (
            FulfillmentPlanStatus.PARTIALLY_FULFILLED
            if any(
                not allocation.fulfilled_qty.value.is_zero()
                for allocation in allocations
            )
            else (
                FulfillmentPlanStatus.CONFIRMED
                if all(
                    allocation.reservation is not None
                    for allocation in allocations
                    if allocation.status is not FulfillmentAllocationStatus.CANCELLED
                )
                else FulfillmentPlanStatus.PARTIALLY_CONFIRMED
            )
        )
        return self._changed(
            updated_at=normalized, allocations=allocations, status=status
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
        if any(not row.fulfilled_qty.value.is_zero() for row in allocations):
            status = FulfillmentPlanStatus.PARTIALLY_FULFILLED
        elif all(
            row.reservation is not None
            for row in allocations
            if row.status is not FulfillmentAllocationStatus.CANCELLED
        ):
            status = FulfillmentPlanStatus.CONFIRMED
        elif any(row.reservation is not None for row in allocations):
            status = FulfillmentPlanStatus.PARTIALLY_CONFIRMED
        else:
            status = FulfillmentPlanStatus.PLANNED
        return self._changed(
            updated_at=normalized, allocations=allocations, status=status
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
        status = (
            FulfillmentPlanStatus.FULFILLED
            if all(
                allocation.fulfilled_qty == allocation.quantity
                for allocation in allocations
                if allocation.status is not FulfillmentAllocationStatus.CANCELLED
            )
            else FulfillmentPlanStatus.PARTIALLY_FULFILLED
        )
        return self._changed(
            updated_at=normalized, allocations=allocations, status=status
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
        active = tuple(
            row
            for row in allocations
            if row.status is not FulfillmentAllocationStatus.CANCELLED
        )
        if not active:
            status = FulfillmentPlanStatus.CANCELLED
        elif all(row.fulfilled_qty == row.quantity for row in active):
            status = FulfillmentPlanStatus.FULFILLED
        elif any(not row.fulfilled_qty.value.is_zero() for row in active):
            status = FulfillmentPlanStatus.PARTIALLY_FULFILLED
        elif all(row.reservation is not None for row in active):
            status = FulfillmentPlanStatus.CONFIRMED
        elif any(row.reservation is not None for row in active):
            status = FulfillmentPlanStatus.PARTIALLY_CONFIRMED
        else:
            status = FulfillmentPlanStatus.PLANNED
        return self._changed(
            updated_at=normalized, allocations=allocations, status=status
        )

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
        return bool(active) and all(row.reservation is not None for row in active)

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
        for allocation in self.allocations:
            if not isinstance(allocation, FulfillmentAllocation):
                raise InvalidFulfillmentAllocationError(
                    "Состав плана содержит только FulfillmentAllocation."
                )
            allocation.ensure_valid()
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
                confirmed += 1
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
        active = self._active_allocations()
        any_fulfilled = any(
            not allocation.fulfilled_qty.value.is_zero()
            for allocation in self.allocations
        )
        all_fulfilled = bool(active) and all(
            allocation.fulfilled_qty == allocation.quantity for allocation in active
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
            not in (FulfillmentPlanStatus.DRAFT, FulfillmentPlanStatus.CANCELLED)
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
        ):
            raise InvalidFulfillmentPlanValueError(
                "Статус плана не соответствует подтверждениям и накопленному исполнению распределений."
            )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Нормализует явно переданное время в UTC без чтения часов или внешней инфраструктуры."""
        return normalize_fulfillment_time(value)
