from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class DeleteVariantCommand:
    product_id: ProductIdVO
    variant_id: VariantIdVO
    actor_id: EntityIdVO
