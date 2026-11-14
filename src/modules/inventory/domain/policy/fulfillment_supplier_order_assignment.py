from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanTimeError,
    FulfillmentSupplierOrderAssignmentError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_dropship_option_snapshot import (
    SupplierDropshipOptionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderDraftSnapshot,
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
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_assignment import (
    FulfillmentSupplierOrderAssignmentRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_quantity_terms import (
    FulfillmentSupplierQuantityTermsVO,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)


class FulfillmentSupplierOrderAssignmentPolicy:
    """Проверяет полное закрепление черновика и актуальные условия его строк."""

    @staticmethod
    def build_assignments(
        *,
        plan_id: FulfillmentPlanIdVO,
        plan_version: int,
        allocations: tuple[FulfillmentAllocation, ...],
        draft: SupplierOrderDraftSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        supplier_options: tuple[SupplierDropshipOptionSnapshot, ...],
        as_of: datetime,
    ) -> dict[FulfillmentAllocationIdVO, FulfillmentSupplierOrderAssignmentRefVO]:
        """Возвращает ссылки ровно выбранных строк после повторной сверки плана и условий."""
        if (
            not isinstance(draft, SupplierOrderDraftSnapshot)
            or not isinstance(inventory_items, tuple)
            or not isinstance(supplier_options, tuple)
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужны снимок черновика и tuple текущих товаров и предложений."
            )
        draft.ensure_valid()
        if draft.plan_id != plan_id or draft.source_plan_version > plan_version:
            raise FulfillmentSupplierOrderAssignmentError(
                "Черновик должен относиться к существующей версии этого плана."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < draft.created_at
        ):
            raise FulfillmentPlanTimeError(
                "Закрепление не может предшествовать созданию черновика."
            )

        selected = {line.allocation.id: line for line in draft.lines}
        current = {row.id: row for row in allocations}
        group = {
            row.id
            for row in allocations
            if row.supplier_order_assignment is not None
            and row.supplier_order_assignment.order_id == draft.order_id
        }
        if not set(selected) <= set(current) or (group and group != set(selected)):
            raise FulfillmentSupplierOrderAssignmentError(
                "Закрепление требует известные распределения и весь состав уже закреплённого заказа."
            )

        items, options = {}, {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemStockSnapshot):
                raise FulfillmentSupplierOrderAssignmentError(
                    "Нужны учётные снимки товаров."
                )
            item.ensure_valid()
            if item.inventory_item_id in items:
                raise FulfillmentSupplierOrderAssignmentError(
                    "Снимок товара повторяется."
                )
            items[item.inventory_item_id] = item
        for option in supplier_options:
            if not isinstance(option, SupplierDropshipOptionSnapshot):
                raise FulfillmentSupplierOrderAssignmentError(
                    "Нужны снимки прямой поставки."
                )
            option.ensure_valid()
            if option.source in options:
                raise FulfillmentSupplierOrderAssignmentError(
                    "Снимок предложения повторяется."
                )
            options[option.source] = option
        if set(items) != {
            line.allocation.inventory_item_id for line in draft.lines
        } or set(options) != {line.allocation.source for line in draft.lines}:
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужны ровно товары и предложения всех строк черновика."
            )

        assignments = {}
        for identifier, line in selected.items():
            row = current[identifier]
            basis = line.allocation
            if row.status is not FulfillmentAllocationStatus.PLANNED or (
                row.source,
                row.inventory_item_id,
                row.base_uom,
                row.quantity,
                row.quoted_purchase_price,
            ) != (
                basis.source,
                basis.inventory_item_id,
                basis.base_uom,
                basis.quantity,
                basis.quoted_purchase_price,
            ):
                raise FulfillmentSupplierOrderAssignmentError(
                    "Распределение должно оставаться плановым с прежними товаром, источником, количеством и ценой."
                )
            previous = row.supplier_order_assignment
            if previous is not None and (
                previous.order_id,
                previous.line_id,
                previous.supplier,
                previous.order_version,
                previous.source_plan_version,
            ) != (
                draft.order_id,
                line.line_id,
                draft.supplier,
                draft.order_version,
                draft.source_plan_version,
            ):
                raise FulfillmentSupplierOrderAssignmentError(
                    "Распределение уже закреплено за другой строкой или внешним заказом."
                )
            option = options[basis.source]
            if option.source_supplier != draft.supplier:
                raise FulfillmentSupplierOrderAssignmentError(
                    "Источник должен принадлежать поставщику черновика."
                )
            item = items[row.inventory_item_id]
            row.ensure_supplier_compatible(inventory_item=item, option=option)
            assignments[identifier] = (
                previous
                or FulfillmentSupplierOrderAssignmentRefVO(
                    draft.order_id,
                    line.line_id,
                    draft.supplier,
                    draft.order_version,
                    draft.source_plan_version,
                    as_of,
                    FulfillmentSupplierQuantityTermsVO(
                        item.quantity_rules.step,
                        option.min_order_qty.value,
                        option.order_multiple.value,
                    ),
                )
            )
        return assignments
