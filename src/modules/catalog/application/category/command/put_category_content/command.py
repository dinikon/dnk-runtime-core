from dataclasses import dataclass

from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True)
class PutCategoryContentCommand:
    category_id: CategoryIdVO
    actor_id: EntityIdVO
    locale: str
    name: str
