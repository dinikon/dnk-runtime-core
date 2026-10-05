from dataclasses import dataclass
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True)
class MoveCategoryCommand:
    tenant_id: EntityIdVO
    category_id: CategoryIdVO
    parent_id: CategoryIdVO | None
    actor_id: EntityIdVO
