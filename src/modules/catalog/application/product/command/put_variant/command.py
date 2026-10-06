from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class PutVariantCommand:
    product_id: ProductIdVO
    variant_id: VariantIdVO
    actor_id: EntityIdVO
    sku_id: UUID
