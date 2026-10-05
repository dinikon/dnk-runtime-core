from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True)
class PutProductCategoriesCommand:
    product_id: ProductIdVO
    actor_id: EntityIdVO
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
