from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True, slots=True)
class SetProductCategoriesCommand:
    """Полная замена categories с проверкой ревизии товара."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    category_ids: tuple[CategoryIdVO, ...]
    primary_category_id: CategoryIdVO | None
