from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.attribute_value import (
    ProductAttributeValueVO,
)


@dataclass(frozen=True, slots=True)
class SetProductAttributesCommand:
    """Полная замена attributes с проверкой ревизии товара."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    values: tuple[ProductAttributeValueVO, ...]
