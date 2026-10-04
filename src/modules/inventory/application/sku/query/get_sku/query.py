from dataclasses import dataclass

from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO


@dataclass(frozen=True, slots=True)
class GetSkuQuery:
    """Чтение одной SKU в текущем tenant."""

    sku_id: SkuIdVO
