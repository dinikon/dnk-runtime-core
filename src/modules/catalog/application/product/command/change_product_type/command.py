from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class ChangeProductTypeCommand:
    """Вход сценария change_product_type; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    product_type_id: ProductTypeIdVO
