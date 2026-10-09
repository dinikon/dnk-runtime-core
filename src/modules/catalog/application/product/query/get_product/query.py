from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO


@dataclass(frozen=True, slots=True)
class GetProductQuery:
    """Вход сценария get_product; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    product_id: ProductIdVO
    locale: str
