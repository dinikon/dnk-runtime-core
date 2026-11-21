from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.demand_snapshot import (
    FulfillmentDemandSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentReplanningConflictError,
    FulfillmentPlanTimeError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.fulfillment_plan import FulfillmentPlanPolicy
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class FulfillmentReplanningPolicy:
    """Проверяет замену не начатых распределений и итоговую потребность без изменения внешних агрегатов."""

    @staticmethod
    def build_allocations(
        *,
        order_ref: FulfillmentOrderRefVO,
        allocations: tuple[FulfillmentAllocation, ...],
        allocation_ids: tuple[FulfillmentAllocationIdVO, ...],
        replacements: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        as_of: datetime,
    ) -> tuple[FulfillmentAllocation, ...]:
        """Возвращает весь кандидат с отменёнными строками после проверки пакета, истории и актуального контекста."""
        if (
            not isinstance(allocations, tuple)
            or not isinstance(allocation_ids, tuple)
            or not allocation_ids
            or not isinstance(replacements, tuple)
            or not replacements
        ):
            raise FulfillmentReplanningConflictError(
                "Нужны tuple состава, непустых ID замены и новых распределений."
            )
        if not isinstance(as_of, datetime) or as_of.utcoffset() != timedelta(0):
            raise FulfillmentPlanTimeError(
                "Перепланирование требует явное время в UTC."
            )
        by_id = {}
        for row in allocations:
            if not isinstance(row, FulfillmentAllocation):
                raise FulfillmentReplanningConflictError(
                    "Состав содержит только дочерние распределения."
                )
            row.ensure_valid()
            if row.id in by_id:
                raise FulfillmentReplanningConflictError(
                    "ID распределения повторяется."
                )
            by_id[row.id] = row
        selected = set()
        for identifier in allocation_ids:
            if (
                not isinstance(identifier, FulfillmentAllocationIdVO)
                or identifier in selected
                or identifier not in by_id
            ):
                raise FulfillmentReplanningConflictError(
                    "Выберите существующие уникальные типизированные ID распределений."
                )
            selected.add(identifier)
            if (
                not isinstance(by_id[identifier].source, FulfillmentSourceRefVO)
                or by_id[identifier].status is not FulfillmentAllocationStatus.PLANNED
            ):
                raise FulfillmentReplanningConflictError(
                    "Для замены выбираются только действующие складские PLANNED."
                )
        # Entity проверяет локальный переход до проверки внешнего контекста всего кандидата.
        cancelled = {
            identifier: by_id[identifier].cancel_unstarted(cancelled_at=as_of)
            for identifier in selected
        }
        sources = {
            by_id[identifier].source_ref: (
                by_id[identifier].inventory_item_id,
                by_id[identifier].base_uom,
            )
            for identifier in selected
        }
        new_ids = set()
        for row in replacements:
            if not isinstance(row, FulfillmentAllocation):
                raise FulfillmentReplanningConflictError(
                    "Замены содержат только новые дочерние распределения."
                )
            row.ensure_valid()
            if (
                row.id in by_id
                or row.id in new_ids
                or not isinstance(row.source, FulfillmentSourceRefVO)
                or row.status is not FulfillmentAllocationStatus.PLANNED
                or row.reservation_releases
                or row.reservation is not None
                or row.shipment_assignment is not None
                or row.shipment_progress is not None
                or not row.fulfilled_qty.value.is_zero()
                or row.source_ref not in sources
                or sources[row.source_ref] != (row.inventory_item_id, row.base_uom)
            ):
                raise FulfillmentReplanningConflictError(
                    "Нужны новые PLANNED без истории для выбранных строк и прежних товара/единицы."
                )
            new_ids.add(row.id)
        candidate = (
            tuple(cancelled.get(row.id, row) for row in allocations) + replacements
        )
        FulfillmentPlanPolicy.ensure_confirmable_reservations(
            order_ref=order_ref,
            allocations=candidate,
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
        )
        return candidate
