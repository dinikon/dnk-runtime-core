from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentReservationReleaseConflictError,
    FulfillmentPlanTimeError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_binding import (
    FulfillmentReservationBindingVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_release import (
    FulfillmentReservationReleaseRefVO,
)
from src.modules.inventory.domain.stock_reservation.fulfillment_snapshot import (
    StockReservationFulfillmentSnapshot,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO


class FulfillmentReservationReleasePolicy:
    """Проверяет закрытые без погашения резервы для снятия подтверждений без изменения чужих агрегатов."""

    @staticmethod
    def build_releases(
        *,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocation, ...],
        bindings: tuple[FulfillmentReservationBindingVO, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        as_of: datetime,
    ) -> dict[FulfillmentAllocationIdVO, FulfillmentReservationReleaseRefVO]:
        """Возвращает новые записи либо прежние записи точного повтора после проверки всего выбранного пакета."""
        if (
            not isinstance(owner_id, StockOwnerIdVO)
            or not isinstance(allocations, tuple)
            or not isinstance(bindings, tuple)
            or not bindings
            or not isinstance(reservations, tuple)
        ):
            raise FulfillmentReservationReleaseConflictError(
                "Нужны владелец и tuple распределений, непустых назначений и закрытых резервов."
            )
        if not isinstance(as_of, datetime) or as_of.utcoffset() != timedelta(0):
            raise FulfillmentPlanTimeError(
                "Снятие подтверждений требует явное время в UTC."
            )
        by_allocation = {}
        for allocation in allocations:
            if not isinstance(allocation, FulfillmentAllocation):
                raise FulfillmentReservationReleaseConflictError(
                    "Нужны дочерние распределения плана."
                )
            allocation.ensure_valid()
            if allocation.id in by_allocation:
                raise FulfillmentReservationReleaseConflictError(
                    "Распределение плана повторяется."
                )
            by_allocation[allocation.id] = allocation
        selected, ids = {}, set()
        for binding in bindings:
            if not isinstance(binding, FulfillmentReservationBindingVO):
                raise FulfillmentReservationReleaseConflictError(
                    "Нужны типизированные ID распределения/резерва и выбранная версия закрытия."
                )
            if (
                binding.allocation_id not in by_allocation
                or binding.allocation_id in selected
                or binding.reservation_id in ids
            ):
                raise FulfillmentReservationReleaseConflictError(
                    "Неизвестное или повторное распределение/резерв в пакете снятия."
                )
            selected[binding.allocation_id] = binding
            ids.add(binding.reservation_id)
        snapshots = {}
        for snapshot in reservations:
            if not isinstance(snapshot, StockReservationFulfillmentSnapshot):
                raise FulfillmentReservationReleaseConflictError(
                    "Нужен полный специализированный снимок закрытого резерва."
                )
            snapshot.ensure_valid()
            if snapshot.id in snapshots:
                raise FulfillmentReservationReleaseConflictError(
                    "Снимок резерва повторяется."
                )
            snapshots[snapshot.id] = snapshot
        if set(snapshots) != ids:
            raise FulfillmentReservationReleaseConflictError(
                "Нужны ровно выбранные закрытые резервы без пропусков и лишних снимков."
            )
        result = {}
        for allocation_id, binding in selected.items():
            allocation = by_allocation[allocation_id]
            snapshot = snapshots[binding.reservation_id]
            if (
                allocation.shipment_assignment is not None
                or allocation.shipment_progress is not None
                or not allocation.fulfilled_qty.value.is_zero()
            ):
                raise FulfillmentReservationReleaseConflictError(
                    "Назначенное или исполненное распределение не допускает снятие подтверждения."
                )
            if as_of < snapshot.updated_at:
                raise FulfillmentPlanTimeError(
                    "Снятие не может предшествовать закрытию резерва."
                )
            if (
                snapshot.version != binding.reservation_version
                or snapshot.status
                not in (StockReservationStatus.RELEASED, StockReservationStatus.EXPIRED)
                or not snapshot.reserved_qty.value.is_zero()
                or not snapshot.consumed_qty.value.is_zero()
                or snapshot.requested_qty != allocation.quantity
                or snapshot.source_ref != allocation.source_ref
                or snapshot.key.inventory_item_id != allocation.inventory_item_id
                or snapshot.key.warehouse_id != allocation.source.warehouse_id
                or snapshot.key.owner_id != owner_id
                or snapshot.base_uom != allocation.base_uom
            ):
                raise FulfillmentReservationReleaseConflictError(
                    "Резерв должен быть закрыт выбранной версией без удержания/погашения и соответствовать всей идентичности распределения."
                )
            confirmation = allocation.reservation
            if confirmation is not None:
                if confirmation.reservation_id != snapshot.id:
                    raise FulfillmentReservationReleaseConflictError(
                        "Старое снятие не может удалить новое активное подтверждение."
                    )
                result[allocation_id] = FulfillmentReservationReleaseRefVO(
                    confirmation,
                    snapshot.version,
                    snapshot.status,
                    snapshot.updated_at,
                    as_of,
                )
            else:
                previous = next(
                    (
                        record
                        for record in allocation.reservation_releases
                        if record.confirmation.reservation_id == snapshot.id
                    ),
                    None,
                )
                if previous is None or (
                    previous.closed_version,
                    previous.closed_status,
                    previous.closed_at,
                ) != (snapshot.version, snapshot.status, snapshot.updated_at):
                    raise FulfillmentReservationReleaseConflictError(
                        "Нет такого прежнего снятия либо повтор содержит другие данные закрытия."
                    )
                result[allocation_id] = previous
        return result
