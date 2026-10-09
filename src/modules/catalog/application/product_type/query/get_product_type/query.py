from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class GetProductTypeQuery:
    """Вход сценария get_product_type; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    product_type_id: ProductTypeIdVO
    locale: str
