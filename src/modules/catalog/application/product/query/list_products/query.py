from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class ListProductsQuery:
    """Вход сценария list_products; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    locale: str
    search: str = ""
    page: int = 1
    page_size: int = 20
    product_type_id: ProductTypeIdVO | None = None
    kind: str | None = None
