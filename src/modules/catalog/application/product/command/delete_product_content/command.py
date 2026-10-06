from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class DeleteProductContentCommand:
    product_id: ProductIdVO
    locale: str
    actor_id: EntityIdVO
