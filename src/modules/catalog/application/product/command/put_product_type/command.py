from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class PutProductTypeCommand:
    product_id: ProductIdVO
    product_type_id: ProductTypeIdVO
    expected_schema_version: int
    actor_id: EntityIdVO
