from dataclasses import dataclass

from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class UpdateProductCommand:
    """Команда application-слоя на обновление товара tenant."""

    tenant_id: EntityIdVO
    product_id: ProductIdVO
    sku: str
    product_name: str
    description: str | None = None
    category_id: CategoryIdVO | None = None
