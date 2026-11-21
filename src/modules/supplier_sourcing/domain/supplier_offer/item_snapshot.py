from dataclasses import dataclass

from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    InvalidSupplierOfferValueError,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import (
    SupplierOfferUomCodeVO,
)
from src.modules.supplier_sourcing.domain.value_object.inventory_item_id import (
    SupplierInventoryItemIdVO,
)


@dataclass(frozen=True, slots=True)
class SupplierOfferItemSnapshot:
    """Фиксирует товар и его базовую единицу для нового предложения."""

    inventory_item_id: SupplierInventoryItemIdVO
    base_uom: SupplierOfferUomCodeVO

    def ensure_valid(self) -> None:
        """Проверяет наличие типизированной ссылки на товар и его базовой единицы."""
        if not isinstance(
            self.inventory_item_id, SupplierInventoryItemIdVO
        ) or not isinstance(self.base_uom, SupplierOfferUomCodeVO):
            raise InvalidSupplierOfferValueError(
                "Нужен снимок товара с типизированными идентификатором и базовой единицей."
            )
