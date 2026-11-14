from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_reference import (
    FulfillmentSupplierReferenceVO,
)
from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanContextError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierSourceIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class SupplierDropshipOptionSnapshot:
    """Передаёт свойства выбранного источника и предложения для ручного планирования."""

    source: SupplierDropshipSourceRefVO
    source_supplier: FulfillmentSupplierReferenceVO
    offer_supplier: FulfillmentSupplierReferenceVO
    offer_source_id: FulfillmentSupplierSourceIdVO | None
    source_is_active: bool
    source_supports_dropship: bool
    offer_is_active: bool
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    purchase_price: MoneyVO
    min_order_qty: QuantityVO
    order_multiple: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет типизированные поля предложения, источника и коммерческих условий."""
        if (
            not isinstance(self.source, SupplierDropshipSourceRefVO)
            or not isinstance(self.source_supplier, FulfillmentSupplierReferenceVO)
            or not isinstance(self.offer_supplier, FulfillmentSupplierReferenceVO)
            or (
                self.offer_source_id is not None
                and not isinstance(self.offer_source_id, FulfillmentSupplierSourceIdVO)
            )
            or type(self.source_is_active) is not bool
            or type(self.source_supports_dropship) is not bool
            or type(self.offer_is_active) is not bool
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.purchase_price, MoneyVO)
            or not isinstance(self.purchase_price.amount, Decimal)
            or not self.purchase_price.amount.is_finite()
            or self.purchase_price.amount < 0
            or not isinstance(self.min_order_qty, QuantityVO)
            or self.min_order_qty.value.is_zero()
            or not isinstance(self.order_multiple, QuantityVO)
            or self.order_multiple.value.is_zero()
        ):
            raise FulfillmentPlanContextError(
                "Нужны типизированные данные предложения, неотрицательная цена и положительные минимум и кратность."
            )
