from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanContextError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class SupplierOrderAllocationSnapshot:
    """Передаёт целое плановое распределение поставщику и согласованную цену."""

    id: FulfillmentAllocationIdVO
    source: SupplierDropshipSourceRefVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    quoted_purchase_price: MoneyVO

    def ensure_valid(self) -> None:
        """Проверяет тип источника, ссылки, положительное количество и цену."""
        if (
            not isinstance(self.id, FulfillmentAllocationIdVO)
            or not isinstance(self.source, SupplierDropshipSourceRefVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.quoted_purchase_price, MoneyVO)
            or not isinstance(self.quoted_purchase_price.amount, Decimal)
            or not self.quoted_purchase_price.amount.is_finite()
            or self.quoted_purchase_price.amount < 0
        ):
            raise FulfillmentPlanContextError(
                "Нужны данные целого распределения прямой поставки с количеством и ценой."
            )


@dataclass(frozen=True, slots=True)
class SupplierOrderBasisSnapshot:
    """Фиксирует версию плана и явно выбранные внешние распределения."""

    plan_id: FulfillmentPlanIdVO
    plan_version: int
    plan_updated_at: datetime
    allocations: tuple[SupplierOrderAllocationSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует непустой уникальный набор строк и время основания в UTC."""
        if (
            not isinstance(self.plan_id, FulfillmentPlanIdVO)
            or type(self.plan_version) is not int
            or self.plan_version < 0
            or not isinstance(self.plan_updated_at, datetime)
            or self.plan_updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.allocations, tuple)
            or not self.allocations
        ):
            raise FulfillmentPlanContextError(
                "Нужно основание плана с версией, временем UTC и выбранными распределениями."
            )
        identifiers = set()
        for row in self.allocations:
            if not isinstance(row, SupplierOrderAllocationSnapshot):
                raise FulfillmentPlanContextError("Нужны снимки внешних распределений.")
            row.ensure_valid()
            if row.id in identifiers:
                raise FulfillmentPlanContextError(
                    "Внешнее распределение выбрано дважды."
                )
            identifiers.add(row.id)
