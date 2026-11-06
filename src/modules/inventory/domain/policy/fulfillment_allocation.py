from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentAllocationError,
    FulfillmentPlanContextError,
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
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class FulfillmentAllocationPolicy:
    """Проверяет текущее количество товара и активность выбранного собственного склада без оценки доступного запаса."""

    @staticmethod
    def ensure_item(
        *,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        quantity: QuantityVO,
        inventory_item: InventoryItemStockSnapshot,
    ) -> None:
        """Запрещает смену товара/базовой единицы и требует положительное количество по текущему шагу."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise FulfillmentPlanContextError("Нужен текущий учётный снимок товара.")
        inventory_item.ensure_valid()
        if (
            not isinstance(inventory_item_id, InventoryItemIdVO)
            or not isinstance(base_uom, UomCodeVO)
            or not isinstance(quantity, QuantityVO)
            or quantity.value.is_zero()
        ):
            raise InvalidFulfillmentAllocationError(
                "Нужны товар, базовая единица и положительное QuantityVO."
            )
        if (
            inventory_item_id != inventory_item.inventory_item_id
            or base_uom != inventory_item.base_uom
        ):
            raise FulfillmentPlanContextError(
                "Товар и базовая единица распределения должны совпадать с текущей карточкой."
            )
        QuantityValidationPolicy.validate(
            quantity=quantity, rules=inventory_item.quantity_rules
        )

    @staticmethod
    def ensure_warehouse(
        *, source: FulfillmentSourceRefVO, warehouse: WarehouseSnapshot
    ) -> None:
        """Требует снимок выбранного активного склада без локаций, резервов и физических позиций."""
        if not isinstance(source, FulfillmentSourceRefVO) or not isinstance(
            warehouse, WarehouseSnapshot
        ):
            raise FulfillmentPlanContextError(
                "Нужны типизированные источник и снимок склада."
            )
        warehouse.ensure_valid()
        if source.warehouse_id != warehouse.id:
            raise FulfillmentPlanContextError(
                "Снимок относится к другому складу источника."
            )
        if not warehouse.is_active:
            raise WarehouseInactiveError(
                "Неактивный склад нельзя выбрать для нового плана исполнения."
            )
