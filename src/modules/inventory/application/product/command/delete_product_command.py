from dataclasses import dataclass

from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteProductCommand:
    """Команда application-слоя на удаление товара tenant."""

    tenant_id: EntityIdVO
    product_id: ProductIdVO
