from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentAllocationError,
    FulfillmentPlanContextError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_dropship_option_snapshot import (
    SupplierDropshipOptionSnapshot,
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
from src.modules.shared.domain.decimal_arithmetic import is_decimal_multiple
from src.modules.shared.domain.value_object.money import MoneyVO


class FulfillmentAllocationPolicy:
    """Проверяет учётные и коммерческие условия выбора источника исполнения."""

    @staticmethod
    def ensure_supplier_option(
        *,
        source: SupplierDropshipSourceRefVO,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        quantity: QuantityVO,
        quoted_purchase_price: MoneyVO,
        option: SupplierDropshipOptionSnapshot,
    ) -> None:
        """Сверяет внешний источник, товар, текущую цену и коммерческую кратность."""
        if not isinstance(option, SupplierDropshipOptionSnapshot):
            raise FulfillmentPlanContextError("Нужен снимок выбранной прямой поставки.")
        option.ensure_valid()
        if (
            source != option.source
            or option.source_supplier_id != option.offer_supplier_id
            or (
                option.offer_source_id is not None
                and option.offer_source_id != source.supplier_source_id
            )
            or inventory_item_id != option.inventory_item_id
            or base_uom != option.base_uom
        ):
            raise FulfillmentPlanContextError(
                "Поставщик, источник, предложение, товар и базовая единица должны совпадать."
            )
        if not (
            option.source_is_active
            and option.source_supports_dropship
            and option.offer_is_active
        ):
            raise FulfillmentPlanContextError(
                "Для прямой поставки нужны активное предложение и активный источник с режимом DROPSHIP."
            )
        if quoted_purchase_price != option.purchase_price:
            raise FulfillmentPlanContextError(
                "Цена предложения изменилась. Выберите его заново."
            )
        if quantity.value < option.min_order_qty.value or not is_decimal_multiple(
            quantity.value, option.order_multiple.value
        ):
            raise InvalidFulfillmentAllocationError(
                "Количество должно достигать минимума и быть кратно коммерческому шагу поставщика."
            )

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
        *,
        source: FulfillmentSourceRefVO | SupplierDropshipSourceRefVO,
        warehouse: WarehouseSnapshot,
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
