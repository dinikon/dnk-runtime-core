from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.fulfillment_plan.supplier_dropship_option_snapshot import (
    SupplierDropshipOptionSnapshot,
)
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
    FulfillmentSupplierOrderAssignmentError,
    FulfillmentSupplierOrderConfirmationError,
    FulfillmentSupplierOrderRejectionError,
    FulfillmentSupplierOrderShipmentError,
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
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class FulfillmentAllocation:
    """Дочернее распределение строки заказа с исторической ссылкой полного подтверждения и без прямого изменения резерва."""

    id: FulfillmentAllocationIdVO
    source_ref: ReservationSourceVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    source: FulfillmentSourceRefVO | SupplierDropshipSourceRefVO
    quantity: QuantityVO
    status: FulfillmentAllocationStatus
    reservation: FulfillmentReservationRefVO | None
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

    @classmethod
    def create(
        cls,
        *,
        identifier: FulfillmentAllocationIdVO,
        source_ref: ReservationSourceVO,
        inventory_item: InventoryItemStockSnapshot,
        source: FulfillmentSourceRefVO | SupplierDropshipSourceRefVO,
        quantity: QuantityVO,
        quoted_purchase_price: MoneyVO | None = None,
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
            quoted_purchase_price=quoted_purchase_price,
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
        source: FulfillmentSourceRefVO | SupplierDropshipSourceRefVO,
        quantity: QuantityVO,
        status: FulfillmentAllocationStatus,
        reservation: FulfillmentReservationRefVO | None,
        fulfilled_qty: QuantityVO,
        shipment_progress: FulfillmentShipmentProgressRefVO | None,
        shipment_assignment: FulfillmentShipmentAssignmentRefVO | None,
        reservation_releases: tuple[FulfillmentReservationReleaseRefVO, ...],
        cancelled_at: datetime | None,
        quoted_purchase_price: MoneyVO | None = None,
        supplier_order_assignment: (
            FulfillmentSupplierOrderAssignmentRefVO | None
        ) = None,
        supplier_confirmation: FulfillmentSupplierOrderConfirmationRefVO | None = None,
        supplier_confirmed_qty: QuantityVO | None = None,
        supplier_rejection: FulfillmentSupplierOrderRejectionRefVO | None = None,
        supplier_shipment: FulfillmentSupplierOrderShipmentRefVO | None = None,
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
            quoted_purchase_price,
            supplier_order_assignment,
            supplier_confirmation,
            supplier_confirmed_qty,
            supplier_rejection,
            supplier_shipment,
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
            or not isinstance(
                self.source, (FulfillmentSourceRefVO, SupplierDropshipSourceRefVO)
            )
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.status, FulfillmentAllocationStatus)
            or (
                self.supplier_confirmed_qty is not None
                and (
                    not isinstance(self.supplier_confirmed_qty, QuantityVO)
                    or self.supplier_confirmation is None
                )
            )
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
            != self.is_confirmed()
            or not isinstance(self.fulfilled_qty, QuantityVO)
            or self.fulfilled_qty.value > self.quantity_to_fulfill().value
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
        self._ensure_source_state()
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
        full = self.fulfilled_qty == self.quantity_to_fulfill()
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
            or (
                not zero
                and self.shipment_progress is None
                and self.supplier_shipment is None
            )
        ):
            raise InvalidFulfillmentAllocationError(
                "Статус, исполненное количество и контрольная точка распределения не согласованы."
            )

    def confirm_reservation(self, reservation: FulfillmentReservationRefVO) -> Self:
        """Фиксирует проверенную корнем ссылку ровно один раз, сохраняя количество и все исходные привязки."""
        self.ensure_valid()
        if (
            not isinstance(self.source, FulfillmentSourceRefVO)
            or self.status is not FulfillmentAllocationStatus.PLANNED
        ):
            raise FulfillmentReservationConflictError(
                "Резервом подтверждается только плановое складское распределение."
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
            or self.supplier_order_assignment is not None
            or not self.fulfilled_qty.value.is_zero()
        ):
            raise FulfillmentAllocationCancellationConflictError(
                "Отменяется только PLANNED без резерва, назначения и исполнения."
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
        return QuantityArithmeticPolicy.subtract(
            self.quantity_to_fulfill(), self.fulfilled_qty
        )

    def quantity_to_fulfill(self) -> QuantityVO:
        """Возвращает действующее количество по ответу поставщика или исходному плану."""
        return (
            self.quantity
            if self.supplier_confirmed_qty is None
            else self.supplier_confirmed_qty
        )

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

    def ensure_supplier_compatible(
        self,
        *,
        inventory_item: InventoryItemStockSnapshot,
        option: SupplierDropshipOptionSnapshot,
    ) -> None:
        """Повторно проверяет товар, учётный шаг и условия прямой поставки."""
        self.ensure_valid()
        if (
            not isinstance(self.source, SupplierDropshipSourceRefVO)
            or self.quoted_purchase_price is None
        ):
            raise FulfillmentPlanContextError(
                "Нужно распределение прямой поставки с зафиксированной ценой."
            )
        FulfillmentAllocationPolicy.ensure_item(
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            quantity=self.quantity,
            inventory_item=inventory_item,
        )
        FulfillmentAllocationPolicy.ensure_supplier_option(
            source=self.source,
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            quantity=self.quantity,
            quoted_purchase_price=self.quoted_purchase_price,
            option=option,
        )

    def assign_supplier_order(
        self, assignment: FulfillmentSupplierOrderAssignmentRefVO
    ) -> Self:
        """Закрепляет плановую прямую поставку за одной строкой внешнего заказа."""
        self.ensure_valid()
        if not isinstance(assignment, FulfillmentSupplierOrderAssignmentRefVO):
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужна ссылка назначения внешнего заказа."
            )
        if self.supplier_order_assignment == assignment:
            return self
        if self.supplier_order_assignment is not None:
            raise FulfillmentSupplierOrderAssignmentError(
                "Распределение уже закреплено за внешним заказом."
            )
        updated = replace(self, supplier_order_assignment=assignment)
        updated.ensure_valid()
        return updated

    def is_confirmed(self) -> bool:
        """Определяет наличие подтверждения по одному из двух маршрутов исполнения."""
        return self.reservation is not None or (
            self.supplier_confirmation is not None
            and not self.quantity_to_fulfill().value.is_zero()
        )

    def confirm_supplier_order(
        self,
        confirmation: FulfillmentSupplierOrderConfirmationRefVO,
        quantity: QuantityVO,
    ) -> Self:
        """Сохраняет проверенное корнем подтверждение закреплённого внешнего заказа."""
        self.ensure_valid()
        if not isinstance(
            confirmation, FulfillmentSupplierOrderConfirmationRefVO
        ) or not isinstance(quantity, QuantityVO):
            raise FulfillmentSupplierOrderConfirmationError(
                "Нужны ссылка ответа поставщика и подтверждённое количество."
            )
        if self.supplier_confirmation is not None:
            if (
                self.supplier_confirmation == confirmation
                and self.quantity_to_fulfill() == quantity
            ):
                return self
            raise FulfillmentSupplierOrderConfirmationError(
                "Уже зарегистрированное подтверждение нельзя изменить."
            )
        if self.status is not FulfillmentAllocationStatus.PLANNED:
            raise FulfillmentSupplierOrderConfirmationError(
                "Подтверждается только закреплённая плановая прямая поставка."
            )
        is_cancelled = quantity.value.is_zero()
        updated = replace(
            self,
            supplier_confirmation=confirmation,
            supplier_confirmed_qty=quantity,
            status=(
                FulfillmentAllocationStatus.CANCELLED
                if is_cancelled
                else FulfillmentAllocationStatus.CONFIRMED
            ),
            cancelled_at=confirmation.confirmed_at if is_cancelled else None,
        )
        updated.ensure_valid()
        return updated

    def register_supplier_shipment(
        self, shipment: FulfillmentSupplierOrderShipmentRefVO, quantity: QuantityVO
    ) -> Self:
        """Фиксирует исполнение всей подтверждённой внешней строки."""
        self.ensure_valid()
        if (
            not isinstance(shipment, FulfillmentSupplierOrderShipmentRefVO)
            or not isinstance(quantity, QuantityVO)
            or self.supplier_confirmation is None
            or quantity.value.is_zero()
            or quantity != self.quantity_to_fulfill()
        ):
            raise FulfillmentSupplierOrderShipmentError(
                "Отправка должна закрывать положительное подтверждение внешней строки."
            )
        if self.supplier_shipment == shipment:
            return self
        if self.status is not FulfillmentAllocationStatus.CONFIRMED:
            raise FulfillmentSupplierOrderShipmentError(
                "Новая отправка требует подтверждённую внешнюю строку без исполнения."
            )
        updated = replace(
            self,
            status=FulfillmentAllocationStatus.FULFILLED,
            fulfilled_qty=quantity,
            supplier_shipment=shipment,
        )
        updated.ensure_valid()
        return updated

    def reject_supplier_order(
        self, rejection: FulfillmentSupplierOrderRejectionRefVO
    ) -> Self:
        """Закрывает закреплённую строку с сохранением исходного запроса и отказа."""
        self.ensure_valid()
        if not isinstance(rejection, FulfillmentSupplierOrderRejectionRefVO):
            raise FulfillmentSupplierOrderRejectionError(
                "Нужна ссылка отказа поставщика."
            )
        if self.supplier_rejection == rejection:
            return self
        if (
            self.status is not FulfillmentAllocationStatus.PLANNED
            or self.supplier_order_assignment is None
        ):
            raise FulfillmentSupplierOrderRejectionError(
                "Отказ закрывает только закреплённую плановую строку."
            )
        updated = replace(
            self,
            supplier_rejection=rejection,
            status=FulfillmentAllocationStatus.CANCELLED,
            cancelled_at=rejection.rejected_at,
        )
        updated.ensure_valid()
        return updated

    def _ensure_source_state(self) -> None:
        """Разделяет коммерческое намерение поставщику и складские подтверждения."""
        price = self.quoted_purchase_price
        assignment = self.supplier_order_assignment
        confirmation = self.supplier_confirmation
        rejection = self.supplier_rejection
        if assignment is not None:
            if (
                not isinstance(assignment, FulfillmentSupplierOrderAssignmentRefVO)
                or not isinstance(self.source, SupplierDropshipSourceRefVO)
                or (
                    confirmation is None
                    and rejection is None
                    and self.status is not FulfillmentAllocationStatus.PLANNED
                )
            ):
                raise InvalidFulfillmentAllocationError(
                    "Закрепление требует плановую прямую поставку или сохранённый ответ."
                )
            assignment.ensure_valid()
            if (
                assignment.quantity_terms is not None
                and not assignment.quantity_terms.accepts(self.quantity)
            ):
                raise InvalidFulfillmentAllocationError(
                    "Исходное количество должно соответствовать сохранённым условиям запроса."
                )
        if confirmation is not None:
            if (
                not isinstance(confirmation, FulfillmentSupplierOrderConfirmationRefVO)
                or assignment is None
                or confirmation.order_version != assignment.order_version + 2
                or confirmation.requested_at < assignment.assigned_at
            ):
                raise InvalidFulfillmentAllocationError(
                    "Подтверждение поставщика должно следовать за закреплением того же заказа."
                )
            confirmation.ensure_valid()
            quantity = self.quantity_to_fulfill()
            terms = assignment.quantity_terms
            if (
                quantity.value > self.quantity.value
                or (
                    quantity != self.quantity
                    and (
                        terms is None
                        or (
                            not quantity.value.is_zero() and not terms.accepts(quantity)
                        )
                    )
                )
                or quantity.value.is_zero()
                != (self.status is FulfillmentAllocationStatus.CANCELLED)
                or (
                    quantity.value.is_zero()
                    and self.cancelled_at != confirmation.confirmed_at
                )
            ):
                raise FulfillmentSupplierOrderConfirmationError(
                    "Ответ должен соблюдать сохранённые правила, предел запроса и состояние строки."
                )
        if rejection is not None:
            if (
                not isinstance(rejection, FulfillmentSupplierOrderRejectionRefVO)
                or assignment is None
                or confirmation is not None
                or self.status is not FulfillmentAllocationStatus.CANCELLED
                or self.cancelled_at != rejection.rejected_at
                or rejection.order_version != assignment.order_version + 2
                or rejection.requested_at < assignment.assigned_at
            ):
                raise FulfillmentSupplierOrderRejectionError(
                    "Отказ должен закрывать закреплённую строку без подтверждения."
                )
            rejection.ensure_valid()
        supplier_shipment = self.supplier_shipment
        if supplier_shipment is not None:
            if (
                not isinstance(supplier_shipment, FulfillmentSupplierOrderShipmentRefVO)
                or confirmation is None
                or self.status is not FulfillmentAllocationStatus.FULFILLED
                or supplier_shipment.order_version != confirmation.order_version + 1
                or supplier_shipment.shipped_at < confirmation.confirmed_at
            ):
                raise FulfillmentSupplierOrderShipmentError(
                    "Исполненная внешняя строка требует отправку после её подтверждения."
                )
            supplier_shipment.ensure_valid()
        if isinstance(self.source, SupplierDropshipSourceRefVO):
            if (
                not isinstance(price, MoneyVO)
                or not isinstance(price.amount, Decimal)
                or not price.amount.is_finite()
                or price.amount < 0
                or self.status
                not in (
                    FulfillmentAllocationStatus.PLANNED,
                    FulfillmentAllocationStatus.CONFIRMED,
                    FulfillmentAllocationStatus.FULFILLED,
                    FulfillmentAllocationStatus.CANCELLED,
                )
                or self.reservation is not None
                or self.reservation_releases
                or self.shipment_assignment is not None
                or self.shipment_progress is not None
            ):
                raise InvalidFulfillmentAllocationError(
                    "Внешнее распределение требует цену и состояние прямой поставки без складского исполнения."
                )
        elif price is not None:
            raise InvalidFulfillmentAllocationError(
                "Цена предложения относится только к прямой поставке."
            )
