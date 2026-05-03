from dataclasses import dataclass

from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetProductQuery:
    """Query application-слоя на получение одного товара tenant."""

    tenant_id: EntityIdVO
    product_id: ProductIdVO
