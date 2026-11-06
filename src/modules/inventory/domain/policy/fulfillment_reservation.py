from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanContextError,
    FulfillmentPlanTimeError,
    FulfillmentReservationConflictError,
    FulfillmentReservationMismatchError,
    FulfillmentReservationUnavailableError,
    FulfillmentReservationVersionConflictError,
    InvalidFulfillmentReservationBindingError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_binding import (
    FulfillmentReservationBindingVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_ref import (
    FulfillmentReservationRefVO,
)
from src.modules.inventory.domain.stock_reservation.fulfillment_snapshot import (
    StockReservationFulfillmentSnapshot,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO


class FulfillmentReservationPolicy:
    """Подтверждает новые распределения и прежние ещё не начатые удержания, сохраняя историю уже зарегистрированных Shipment."""

    @staticmethod
    def build_confirmations(
        *,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocation, ...],
        bindings: tuple[FulfillmentReservationBindingVO, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        as_of: datetime,
    ) -> dict[FulfillmentAllocationIdVO, FulfillmentReservationRefVO]:
        """Возвращает новые ссылки после проверки точного набора новых и прежних ещё не начатых удержаний."""
        if (
            not isinstance(owner_id, StockOwnerIdVO)
            or not isinstance(allocations, tuple)
            or not isinstance(reservations, tuple)
        ):
            raise FulfillmentPlanContextError(
                "Нужны владелец и tuple распределений/текущих снимков резервов."
            )
        if not isinstance(as_of, datetime) or as_of.utcoffset() != timedelta(0):
            raise FulfillmentPlanTimeError("Подтверждение требует явное время в UTC.")
        if not isinstance(bindings, tuple) or not bindings:
            raise InvalidFulfillmentReservationBindingError(
                "Нужен непустой tuple новых назначений резервов."
            )
        by_allocation, expected, selected = {}, {}, {}
        used_reservations = set()
        for allocation in allocations:
            if not isinstance(allocation, FulfillmentAllocation):
                raise FulfillmentPlanContextError("Нужны дочерние распределения плана.")
            allocation.ensure_valid()
            if allocation.id in by_allocation:
                raise FulfillmentReservationConflictError("Распределение повторяется.")
            by_allocation[allocation.id] = allocation
            for release in allocation.reservation_releases:
                identifier = release.confirmation.reservation_id
                if identifier in used_reservations:
                    raise FulfillmentReservationConflictError(
                        "Снятый резервный ID повторяется в истории плана."
                    )
                used_reservations.add(identifier)
            if allocation.reservation is not None:
                ref = allocation.reservation
                if as_of < ref.confirmed_at:
                    raise FulfillmentPlanTimeError(
                        "Повторная проверка не может предшествовать прежнему подтверждению."
                    )
                if ref.reservation_id in used_reservations:
                    raise FulfillmentReservationConflictError(
                        "Один резерв закреплён за несколькими распределениями."
                    )
                used_reservations.add(ref.reservation_id)
                if allocation.shipment_progress is None:
                    expected[ref.reservation_id] = (allocation, ref.version)
                elif as_of < allocation.shipment_progress.shipment_updated_at:
                    raise FulfillmentPlanTimeError(
                        "Подтверждение не может предшествовать зарегистрированному прогрессу Shipment."
                    )
        for binding in bindings:
            if not isinstance(binding, FulfillmentReservationBindingVO):
                raise InvalidFulfillmentReservationBindingError(
                    "Нужны типизированные назначения ID и версии резерва."
                )
            allocation = by_allocation.get(binding.allocation_id)
            if allocation is None:
                raise FulfillmentReservationMismatchError(
                    "Назначение относится к отсутствующему распределению."
                )
            if (
                allocation.status is not FulfillmentAllocationStatus.PLANNED
                or binding.allocation_id in selected
                or binding.reservation_id in used_reservations
            ):
                raise FulfillmentReservationConflictError(
                    "Повтор распределения, подтверждения или использования резерва запрещён."
                )
            selected[binding.allocation_id] = binding
            used_reservations.add(binding.reservation_id)
            expected[binding.reservation_id] = (allocation, binding.reservation_version)
        by_reservation = {}
        for reservation in reservations:
            if not isinstance(reservation, StockReservationFulfillmentSnapshot):
                raise FulfillmentPlanContextError(
                    "Нужен специализированный снимок резерва для Fulfillment."
                )
            reservation.ensure_valid()
            if reservation.id in by_reservation:
                raise FulfillmentReservationConflictError("Снимок резерва повторяется.")
            by_reservation[reservation.id] = reservation
        if set(by_reservation) != set(expected):
            raise FulfillmentPlanContextError(
                "Нужны ровно новые и прежние ещё не начатые резервы; снимки уже зарегистрированных Shipment не передаются."
            )
        for identifier, (allocation, version) in expected.items():
            reservation = by_reservation[identifier]
            if reservation.version != version:
                raise FulfillmentReservationVersionConflictError(
                    "Текущая версия резерва отличается от выбранной или ранее подтверждённой."
                )
            if as_of < reservation.updated_at:
                raise FulfillmentPlanTimeError(
                    "Подтверждение не может предшествовать текущему состоянию резерва."
                )
            if reservation.status is not StockReservationStatus.RESERVED or (
                reservation.expires_at is not None and as_of >= reservation.expires_at
            ):
                raise FulfillmentReservationUnavailableError(
                    "Требуется полное открытое удержание с ещё не наступившим сроком."
                )
            if (
                reservation.source_ref != allocation.source_ref
                or reservation.key.inventory_item_id != allocation.inventory_item_id
                or reservation.key.warehouse_id != allocation.source.warehouse_id
                or reservation.key.owner_id != owner_id
                or reservation.base_uom != allocation.base_uom
                or reservation.requested_qty != allocation.quantity
                or reservation.reserved_qty != allocation.quantity
                or not reservation.consumed_qty.value.is_zero()
            ):
                raise FulfillmentReservationMismatchError(
                    "Строка, область, единица, запрос, полное удержание или погашение не соответствуют распределению."
                )
        return {
            identifier: FulfillmentReservationRefVO(
                binding.reservation_id, binding.reservation_version, as_of
            )
            for identifier, binding in selected.items()
        }
