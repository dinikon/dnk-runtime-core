from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class PutVariantContentCommand:
    product_id: ProductIdVO
    variant_id: VariantIdVO
    actor_id: EntityIdVO
    locale: str
    schema_version: int
    blocks: dict[str, str]
