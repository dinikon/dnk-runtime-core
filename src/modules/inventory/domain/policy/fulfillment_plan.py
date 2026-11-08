from decimal import Decimal

from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)

from src.modules.inventory.domain.fulfillment_plan.demand_snapshot import (
    FulfillmentDemandSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    EmptyFulfillmentPlanError,
    FulfillmentAllocationExtensionConflictError,
    FulfillmentDemandExceededError,
    FulfillmentOrderUnavailableError,
    FulfillmentPlanContextError,
    FulfillmentSourceSplitForbiddenError,
    InvalidFulfillmentAllocationError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_dropship_option_snapshot import (
    SupplierDropshipOptionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class FulfillmentPlanPolicy:
    """Проверяет распределение текущей потребности заказа и весь контекст фиксации ручного плана."""

    @staticmethod
    def ensure_extendable(
        *,
        order_ref: FulfillmentOrderRefVO,
        existing_allocations: tuple[FulfillmentAllocation, ...],
        allocations: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
    ) -> None:
        """Требует свежие намерения для свободного спроса и проверяет весь итоговый состав без переоценки удержаний."""
        if (
            not isinstance(existing_allocations, tuple)
            or not isinstance(allocations, tuple)
            or not allocations
        ):
            raise FulfillmentAllocationExtensionConflictError(
                "Нужны tuple прежнего состава и непустого набора новых распределений."
            )
        used_ids = set()
        for row in existing_allocations:
            if not isinstance(row, FulfillmentAllocation):
                raise FulfillmentAllocationExtensionConflictError(
                    "Прежний состав содержит только дочерние распределения."
                )
            row.ensure_valid()
            if row.id in used_ids:
                raise FulfillmentAllocationExtensionConflictError(
                    "ID прежних распределений повторяется."
                )
            used_ids.add(row.id)
        for row in allocations:
            if not isinstance(row, FulfillmentAllocation):
                raise FulfillmentAllocationExtensionConflictError(
                    "Допланирование принимает только новые дочерние распределения."
                )
            row.ensure_valid()
            if (
                row.id in used_ids
                or not isinstance(row.source, FulfillmentSourceRefVO)
                or row.status is not FulfillmentAllocationStatus.PLANNED
                or row.reservation is not None
                or row.reservation_releases
                or row.shipment_assignment is not None
                or row.shipment_progress is not None
                or row.cancelled_at is not None
                or not row.fulfilled_qty.value.is_zero()
            ):
                raise FulfillmentAllocationExtensionConflictError(
                    "Допланирование требует новые складские PLANNED без истории и привязок."
                )
            used_ids.add(row.id)
        FulfillmentPlanPolicy.ensure_confirmable_reservations(
            order_ref=order_ref,
            allocations=(*existing_allocations, *allocations),
            demand=demand,
            inventory_items=inventory_items,
            warehouses=warehouses,
        )

    @staticmethod
    def ensure_demand(
        *,
        order_ref: FulfillmentOrderRefVO,
        allocations: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
    ) -> None:
        """Требует тот же доступный заказ, принадлежность строк, точные суммарные лимиты и разрешённое разделение."""
        if not isinstance(order_ref, FulfillmentOrderRefVO) or not isinstance(
            demand, FulfillmentDemandSnapshot
        ):
            raise FulfillmentPlanContextError(
                "Нужны типизированная ссылка заказа и снимок его потребности."
            )
        demand.ensure_valid()
        if order_ref != demand.order_ref:
            raise FulfillmentPlanContextError("Потребность относится к другому заказу.")
        if not demand.is_fulfillable:
            raise FulfillmentOrderUnavailableError(
                "Заказ недоступен для планирования исполнения."
            )
        if not isinstance(allocations, tuple):
            raise InvalidFulfillmentAllocationError("Распределения передаются в tuple.")
        by_source = {line.source_ref: line for line in demand.lines}
        quantities, sources = {}, {}
        for allocation in allocations:
            if not isinstance(allocation, FulfillmentAllocation):
                raise InvalidFulfillmentAllocationError(
                    "Нужны дочерние распределения плана."
                )
            allocation.ensure_valid()
            if allocation.remaining_to_fulfill().value.is_zero():
                continue
            line = by_source.get(allocation.source_ref)
            if (
                line is None
                or line.inventory_item_id != allocation.inventory_item_id
                or line.base_uom != allocation.base_uom
            ):
                raise FulfillmentPlanContextError(
                    "Строка, товар и базовая единица распределения должны соответствовать потребности заказа."
                )
            previous = quantities.get(line.source_ref, QuantityVO(Decimal(0)))
            total = QuantityArithmeticPolicy.add(
                previous, allocation.remaining_to_fulfill()
            )
            if total.value > line.remaining_qty.value:
                raise FulfillmentDemandExceededError(
                    "Сумма распределений превышает оставшуюся потребность строки заказа."
                )
            quantities[line.source_ref] = total
            selected = sources.setdefault(line.source_ref, set())
            selected.add(allocation.source)
            if not line.allow_source_split and len(selected) > 1:
                raise FulfillmentSourceSplitForbiddenError(
                    "Строка заказа не разрешает распределение между несколькими источниками."
                )

    @staticmethod
    def ensure_plannable(
        *,
        order_ref: FulfillmentOrderRefVO,
        allocations: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        supplier_options: tuple[SupplierDropshipOptionSnapshot, ...] = (),
    ) -> None:
        """Перед PLANNED повторно требует непустой план и ровно участвующие уникальные текущие снимки товаров/складов."""
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=order_ref, allocations=allocations, demand=demand
        )
        if not allocations:
            raise EmptyFulfillmentPlanError(
                "Нельзя зафиксировать пустой план исполнения."
            )
        FulfillmentPlanPolicy._ensure_current_allocations(
            allocations=allocations,
            inventory_items=inventory_items,
            warehouses=warehouses,
            supplier_options=supplier_options,
        )

    @staticmethod
    def ensure_confirmable_reservations(
        *,
        order_ref: FulfillmentOrderRefVO,
        allocations: tuple[FulfillmentAllocation, ...],
        demand: FulfillmentDemandSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
    ) -> None:
        """Проверяет весь оставшийся спрос и текущие настройки только ещё не начатых распределений."""
        FulfillmentPlanPolicy.ensure_demand(
            order_ref=order_ref, allocations=allocations, demand=demand
        )
        FulfillmentPlanPolicy._ensure_current_allocations(
            allocations=tuple(
                row
                for row in allocations
                if row.status is not FulfillmentAllocationStatus.CANCELLED
                and row.shipment_progress is None
                and isinstance(row.source, FulfillmentSourceRefVO)
            ),
            inventory_items=inventory_items,
            warehouses=warehouses,
        )

    @staticmethod
    def _ensure_current_allocations(
        *,
        allocations: tuple[FulfillmentAllocation, ...],
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        warehouses: tuple[WarehouseSnapshot, ...],
        supplier_options: tuple[SupplierDropshipOptionSnapshot, ...] = (),
    ) -> None:
        """Требует ровно участвующие снимки и повторно проверяет каждый вид источника."""
        if (
            not isinstance(inventory_items, tuple)
            or not isinstance(warehouses, tuple)
            or not isinstance(supplier_options, tuple)
        ):
            raise FulfillmentPlanContextError(
                "Снимки товаров, складов и предложений передаются в tuple."
            )
        by_item, by_warehouse, by_supplier = {}, {}, {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemStockSnapshot):
                raise FulfillmentPlanContextError("Нужны учётные снимки товаров плана.")
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise FulfillmentPlanContextError("Снимок товара повторяется.")
            by_item[item.inventory_item_id] = item
        for warehouse in warehouses:
            if not isinstance(warehouse, WarehouseSnapshot):
                raise FulfillmentPlanContextError("Нужны снимки складов плана.")
            warehouse.ensure_valid()
            if warehouse.id in by_warehouse:
                raise FulfillmentPlanContextError("Снимок склада повторяется.")
            by_warehouse[warehouse.id] = warehouse
        for option in supplier_options:
            if not isinstance(option, SupplierDropshipOptionSnapshot):
                raise FulfillmentPlanContextError(
                    "Нужны снимки предложений прямой поставки."
                )
            option.ensure_valid()
            if option.source in by_supplier:
                raise FulfillmentPlanContextError("Снимок прямой поставки повторяется.")
            by_supplier[option.source] = option
        if (
            set(by_item) != {allocation.inventory_item_id for allocation in allocations}
            or set(by_warehouse)
            != {
                row.source.warehouse_id
                for row in allocations
                if isinstance(row.source, FulfillmentSourceRefVO)
            }
            or set(by_supplier)
            != {
                row.source
                for row in allocations
                if isinstance(row.source, SupplierDropshipSourceRefVO)
            }
        ):
            raise FulfillmentPlanContextError(
                "Нужны ровно участвующие товары, склады и предложения без пропусков или лишних снимков."
            )
        for allocation in allocations:
            item = by_item[allocation.inventory_item_id]
            if isinstance(allocation.source, SupplierDropshipSourceRefVO):
                allocation.ensure_supplier_compatible(
                    inventory_item=item, option=by_supplier[allocation.source]
                )
            else:
                allocation.ensure_compatible(
                    inventory_item=item,
                    warehouse=by_warehouse[allocation.source.warehouse_id],
                )
