from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_release import (
    FulfillmentReservationReleaseRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_assignment import (
    FulfillmentShipmentAssignmentRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanContextError,
    FulfillmentAllocationCancellationConflictError,
    FulfillmentPlanTimeError,
    FulfillmentReservationReleaseConflictError,
    FulfillmentShipmentAssignmentConflictError,
    FulfillmentReservationConflictError,
    InvalidFulfillmentAllocationError,
    FulfillmentShipmentProgressMismatchError,
    FulfillmentShipmentProgressConflictError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.shipment_progress_ref import (
    FulfillmentShipmentProgressRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_ref import (
    FulfillmentReservationRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.fulfillment_allocation import (
    FulfillmentAllocationPolicy,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


@dataclass(frozen=True, slots=True)
class FulfillmentAllocation:
    """Дочернее распределение строки заказа с исторической ссылкой полного подтверждения и без прямого изменения резерва."""

    id: FulfillmentAllocationIdVO
    source_ref: ReservationSourceVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    source: FulfillmentSourceRefVO
    quantity: QuantityVO
    status: FulfillmentAllocationStatus
    reservation: FulfillmentReservationRefVO | None
    fulfilled_qty: QuantityVO
    shipment_progress: FulfillmentShipmentProgressRefVO | None
    shipment_assignment: FulfillmentShipmentAssignmentRefVO | None
    reservation_releases: tuple[FulfillmentReservationReleaseRefVO, ...]
    cancelled_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        identifier: FulfillmentAllocationIdVO,
        source_ref: ReservationSourceVO,
        inventory_item: InventoryItemStockSnapshot,
        source: FulfillmentSourceRefVO,
        quantity: QuantityVO,
    ) -> Self:
        """Выводит товар/единицу из снимка и проверяет текущий шаг в базовой единице."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise FulfillmentPlanContextError(
                "Нужен текущий учётный снимок товара распределения."
            )
        inventory_item.ensure_valid()
        allocation = cls.restore(
            identifier=identifier,
            source_ref=source_ref,
            inventory_item_id=inventory_item.inventory_item_id,
            base_uom=inventory_item.base_uom,
            source=source,
            quantity=quantity,
            status=FulfillmentAllocationStatus.PLANNED,
            reservation=None,
            fulfilled_qty=QuantityVO(Decimal(0)),
            shipment_progress=None,
            shipment_assignment=None,
            reservation_releases=(),
            cancelled_at=None,
        )
        FulfillmentAllocationPolicy.ensure_item(
            inventory_item_id=allocation.inventory_item_id,
            base_uom=allocation.base_uom,
            quantity=allocation.quantity,
            inventory_item=inventory_item,
        )
        return allocation

    @classmethod
    def restore(
        cls,
        *,
        identifier: FulfillmentAllocationIdVO,
        source_ref: ReservationSourceVO,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        source: FulfillmentSourceRefVO,
        quantity: QuantityVO,
        status: FulfillmentAllocationStatus,
        reservation: FulfillmentReservationRefVO | None,
        fulfilled_qty: QuantityVO,
        shipment_progress: FulfillmentShipmentProgressRefVO | None,
        shipment_assignment: FulfillmentShipmentAssignmentRefVO | None,
        reservation_releases: tuple[FulfillmentReservationReleaseRefVO, ...],
        cancelled_at: datetime | None,
    ) -> Self:
        """Восстанавливает полный собственный исторический состав без текущего заказа, товара и склада."""
        allocation = cls(
            identifier,
            source_ref,
            inventory_item_id,
            base_uom,
            source,
            quantity,
            status,
            reservation,
            fulfilled_qty,
            shipment_progress,
            shipment_assignment,
            reservation_releases,
            (
                normalize_fulfillment_time(cancelled_at)
                if cancelled_at is not None
                else None
            ),
        )
        allocation.ensure_valid()
        return allocation

    def ensure_valid(self) -> None:
        """Проверяет локальные типы и положительность количества без загрузки чужих объектов."""
        if (
            not isinstance(self.id, FulfillmentAllocationIdVO)
            or not isinstance(self.source_ref, ReservationSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.source, FulfillmentSourceRefVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.status, FulfillmentAllocationStatus)
            or (
                self.reservation is not None
                and not isinstance(self.reservation, FulfillmentReservationRefVO)
            )
            or (
                self.status
                not in (
                    FulfillmentAllocationStatus.PLANNED,
                    FulfillmentAllocationStatus.CANCELLED,
                )
            )
            != (self.reservation is not None)
            or not isinstance(self.fulfilled_qty, QuantityVO)
            or self.fulfilled_qty.value > self.quantity.value
            or (
                self.shipment_progress is not None
                and not isinstance(
                    self.shipment_progress, FulfillmentShipmentProgressRefVO
                )
            )
            or (
                self.shipment_assignment is not None
                and not isinstance(
                    self.shipment_assignment, FulfillmentShipmentAssignmentRefVO
                )
            )
        ):
            raise InvalidFulfillmentAllocationError(
                "Нужны типизированные ссылки, источник, единица и положительное количество распределения."
            )
        get_uom(self.base_uom)
        if not isinstance(self.reservation_releases, tuple):
            raise InvalidFulfillmentAllocationError(
                "История снятий передаётся в tuple."
            )
        released_ids = set()
        previous = None
        for release in self.reservation_releases:
            if not isinstance(release, FulfillmentReservationReleaseRefVO):
                raise InvalidFulfillmentAllocationError(
                    "Нужны типизированные записи истории снятий."
                )
            release.ensure_valid()
            if release.confirmation.reservation_id in released_ids or (
                previous is not None
                and release.confirmation.confirmed_at < previous.released_at
            ):
                raise InvalidFulfillmentAllocationError(
                    "История снятий не повторяет резервные ID и сохраняет последовательность подтверждений."
                )
            released_ids.add(release.confirmation.reservation_id)
            previous = release
        if self.status is FulfillmentAllocationStatus.CANCELLED:
            normalize_fulfillment_time(self.cancelled_at)
            if (
                self.cancelled_at.utcoffset() != timedelta(0)
                or self.shipment_assignment is not None
                or self.shipment_progress is not None
                or not self.fulfilled_qty.value.is_zero()
                or (previous is not None and self.cancelled_at < previous.released_at)
            ):
                raise InvalidFulfillmentAllocationError(
                    "Отменённая строка требует время UTC после снятия резервов и отсутствие назначения/исполнения."
                )
        elif self.cancelled_at is not None:
            raise InvalidFulfillmentAllocationError(
                "Время отмены допустимо только для CANCELLED."
            )
        if self.reservation is not None:
            self.reservation.ensure_valid()
            if self.reservation.reservation_id in released_ids or (
                previous is not None
                and self.reservation.confirmed_at < previous.released_at
            ):
                raise InvalidFulfillmentAllocationError(
                    "Активное подтверждение не использует снятый ID и не предшествует последнему снятию."
                )
        if self.shipment_assignment is not None:
            assignment = self.shipment_assignment
            assignment.ensure_valid()
            if (
                self.reservation is None
                or assignment.assigned_at < self.reservation.confirmed_at
            ):
                raise InvalidFulfillmentAllocationError(
                    "Назначение требует прежнее подтверждение резервом и не может предшествовать ему."
                )
        if self.shipment_progress is not None:
            self.shipment_progress.ensure_valid()
            if (
                self.reservation is None
                or self.shipment_progress.shipment_updated_at
                < self.reservation.confirmed_at
            ):
                raise InvalidFulfillmentAllocationError(
                    "Прогресс требует подтверждение резервом и не может предшествовать ему."
                )
            assignment = self.shipment_assignment
            if (
                assignment is None
                or self.shipment_progress.shipment_id != assignment.shipment_id
                or self.shipment_progress.shipment_line_id
                != assignment.shipment_line_id
                or self.shipment_progress.source_plan_version
                != assignment.source_plan_version
                or self.shipment_progress.shipment_version
                <= assignment.shipment_version
                or self.shipment_progress.shipment_updated_at < assignment.assigned_at
            ):
                raise InvalidFulfillmentAllocationError(
                    "Прогресс должен соответствовать назначению и более новой версии Shipment после назначения."
                )
        zero = self.fulfilled_qty.value.is_zero()
        full = self.fulfilled_qty == self.quantity
        if (
            (
                self.status
                in (
                    FulfillmentAllocationStatus.PLANNED,
                    FulfillmentAllocationStatus.CONFIRMED,
                )
                and not zero
            )
            or (
                self.status is FulfillmentAllocationStatus.PLANNED
                and self.shipment_progress is not None
            )
            or (
                self.status is FulfillmentAllocationStatus.PARTIALLY_FULFILLED
                and (zero or full)
            )
            or (self.status is FulfillmentAllocationStatus.FULFILLED and not full)
            or (not zero and self.shipment_progress is None)
        ):
            raise InvalidFulfillmentAllocationError(
                "Статус, исполненное количество и контрольная точка распределения не согласованы."
            )

    def confirm_reservation(self, reservation: FulfillmentReservationRefVO) -> Self:
        """Фиксирует проверенную корнем ссылку ровно один раз, сохраняя количество и все исходные привязки."""
        self.ensure_valid()
        if self.status is not FulfillmentAllocationStatus.PLANNED:
            raise FulfillmentReservationConflictError(
                "Распределение уже подтверждено; повторная привязка запрещена."
            )
        return self.restore(
            identifier=self.id,
            source_ref=self.source_ref,
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            source=self.source,
            quantity=self.quantity,
            status=FulfillmentAllocationStatus.CONFIRMED,
            reservation=reservation,
            fulfilled_qty=self.fulfilled_qty,
            shipment_progress=self.shipment_progress,
            shipment_assignment=self.shipment_assignment,
            reservation_releases=self.reservation_releases,
            cancelled_at=self.cancelled_at,
        )

    def cancel_unstarted(self, *, cancelled_at: datetime) -> Self:
        """Сохраняет не начатое намерение как терминальную историю без изменения количества и резервных записей."""
        self.ensure_valid()
        normalized = normalize_fulfillment_time(cancelled_at)
        if self.status is FulfillmentAllocationStatus.CANCELLED:
            if normalized < self.cancelled_at:
                raise FulfillmentPlanTimeError(
                    "Повтор отмены не может предшествовать первому моменту отмены."
                )
            return self
        if (
            self.status is not FulfillmentAllocationStatus.PLANNED
            or self.reservation is not None
            or self.shipment_assignment is not None
            or self.shipment_progress is not None
            or not self.fulfilled_qty.value.is_zero()
        ):
            raise FulfillmentAllocationCancellationConflictError(
                "Отменяется только PLANNED без активного резерва, назначения и исполнения."
            )
        changed = replace(
            self,
            status=FulfillmentAllocationStatus.CANCELLED,
            cancelled_at=normalized,
        )
        changed.ensure_valid()
        return changed

    def release_reservation_confirmation(
        self, release: FulfillmentReservationReleaseRefVO
    ) -> Self:
        """Сохраняет проверенное закрытие и возвращает неисполненное неназначенное распределение в PLANNED."""
        self.ensure_valid()
        if not isinstance(release, FulfillmentReservationReleaseRefVO):
            raise FulfillmentReservationReleaseConflictError(
                "Нужна типизированная запись снятия."
            )
        release.ensure_valid()
        if (
            self.shipment_assignment is not None
            or self.shipment_progress is not None
            or not self.fulfilled_qty.value.is_zero()
        ):
            raise FulfillmentReservationReleaseConflictError(
                "Снятие запрещено при назначении Shipment или фактическом исполнении."
            )
        if self.reservation is None:
            if release in self.reservation_releases:
                return self
            raise FulfillmentReservationReleaseConflictError(
                "У распределения нет такого подтверждения для снятия."
            )
        if (
            self.status is not FulfillmentAllocationStatus.CONFIRMED
            or release.confirmation != self.reservation
        ):
            raise FulfillmentReservationReleaseConflictError(
                "Снятие не относится к текущему подтверждению."
            )
        changed = replace(
            self,
            reservation=None,
            status=FulfillmentAllocationStatus.PLANNED,
            reservation_releases=(*self.reservation_releases, release),
        )
        changed.ensure_valid()
        return changed

    def assign_shipment(self, assignment: FulfillmentShipmentAssignmentRefVO) -> Self:
        """Назначает неисполненное распределение либо возвращает его при том же назначении без изменения первого времени."""
        self.ensure_valid()
        if (
            self.status is not FulfillmentAllocationStatus.CONFIRMED
            or self.shipment_progress is not None
        ):
            raise FulfillmentShipmentAssignmentConflictError(
                "Назначается только подтверждённое ещё не начатое распределение."
            )
        if not isinstance(assignment, FulfillmentShipmentAssignmentRefVO):
            raise FulfillmentShipmentAssignmentConflictError(
                "Нужна типизированная ссылка назначения."
            )
        assignment.ensure_valid()
        previous = self.shipment_assignment
        if previous is not None:
            if (
                previous.shipment_id,
                previous.shipment_line_id,
                previous.shipment_version,
                previous.source_plan_version,
            ) != (
                assignment.shipment_id,
                assignment.shipment_line_id,
                assignment.shipment_version,
                assignment.source_plan_version,
            ):
                raise FulfillmentShipmentAssignmentConflictError(
                    "Распределение уже назначено другой строке или версии Shipment."
                )
            return self
        changed = replace(self, shipment_assignment=assignment)
        changed.ensure_valid()
        return changed

    def release_shipment_assignment(self) -> Self:
        """Снимает проверенное корнем назначение только до первого зарегистрированного исполнения."""
        self.ensure_valid()
        if (
            self.status is not FulfillmentAllocationStatus.CONFIRMED
            or self.shipment_progress is not None
        ):
            raise FulfillmentShipmentAssignmentConflictError(
                "Назначение исполненного распределения снять нельзя."
            )
        if self.shipment_assignment is None:
            return self
        changed = replace(self, shipment_assignment=None)
        changed.ensure_valid()
        return changed

    def remaining_to_fulfill(self) -> QuantityVO:
        """Вычисляет точный неисполненный остаток без отдельного хранимого счётчика."""
        self.ensure_valid()
        if self.status is FulfillmentAllocationStatus.CANCELLED:
            return QuantityVO(Decimal(0))
        return QuantityArithmeticPolicy.subtract(self.quantity, self.fulfilled_qty)

    def register_shipment_progress(
        self, *, fulfilled_qty: QuantityVO, progress: FulfillmentShipmentProgressRefVO
    ) -> Self:
        """Принимает накопленный прогресс одной строки, защищая привязку, монотонность и повтор версии."""
        self.ensure_valid()
        if self.status in (
            FulfillmentAllocationStatus.PLANNED,
            FulfillmentAllocationStatus.CANCELLED,
        ):
            raise FulfillmentShipmentProgressMismatchError(
                "Нельзя исполнить неподтверждённое распределение."
            )
        if not isinstance(progress, FulfillmentShipmentProgressRefVO) or not isinstance(
            fulfilled_qty, QuantityVO
        ):
            raise FulfillmentShipmentProgressMismatchError(
                "Нужны типизированная контрольная точка и накопленное количество."
            )
        progress.ensure_valid()
        assignment = self.shipment_assignment
        if (
            assignment is None
            or (
                progress.shipment_id,
                progress.shipment_line_id,
                progress.source_plan_version,
            )
            != (
                assignment.shipment_id,
                assignment.shipment_line_id,
                assignment.source_plan_version,
            )
            or progress.shipment_version <= assignment.shipment_version
            or progress.shipment_updated_at < assignment.assigned_at
        ):
            raise FulfillmentShipmentProgressMismatchError(
                "Прогресс требует прежнее назначение той же строке и более новую версию Shipment."
            )
        if (
            fulfilled_qty.value > self.quantity.value
            or fulfilled_qty.value < self.fulfilled_qty.value
        ):
            raise FulfillmentShipmentProgressConflictError(
                "Прогресс не может уменьшаться или превышать количество распределения."
            )
        previous = self.shipment_progress
        if previous is not None:
            if (
                progress.shipment_id != previous.shipment_id
                or progress.shipment_line_id != previous.shipment_line_id
                or progress.source_plan_version != previous.source_plan_version
            ):
                raise FulfillmentShipmentProgressMismatchError(
                    "Прежнюю строку Shipment и её основание нельзя перепривязать."
                )
            if (
                progress.shipment_version < previous.shipment_version
                or progress.shipment_updated_at < previous.shipment_updated_at
            ):
                raise FulfillmentShipmentProgressConflictError(
                    "Версия или время снимка Shipment устарели."
                )
            if progress.shipment_version == previous.shipment_version:
                if progress != previous or fulfilled_qty != self.fulfilled_qty:
                    raise FulfillmentShipmentProgressConflictError(
                        "Одна версия Shipment не может содержать разные данные."
                    )
                return self
        status = (
            FulfillmentAllocationStatus.FULFILLED
            if fulfilled_qty == self.quantity
            else (
                FulfillmentAllocationStatus.CONFIRMED
                if fulfilled_qty.value.is_zero()
                else FulfillmentAllocationStatus.PARTIALLY_FULFILLED
            )
        )
        changed = replace(
            self, fulfilled_qty=fulfilled_qty, shipment_progress=progress, status=status
        )
        changed.ensure_valid()
        return changed

    def ensure_compatible(
        self,
        *,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
    ) -> None:
        """Повторно проверяет текущие товар/шаг и активный выбранный склад."""
        self.ensure_valid()
        FulfillmentAllocationPolicy.ensure_item(
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            quantity=self.quantity,
            inventory_item=inventory_item,
        )
        FulfillmentAllocationPolicy.ensure_warehouse(
            source=self.source, warehouse=warehouse
        )
