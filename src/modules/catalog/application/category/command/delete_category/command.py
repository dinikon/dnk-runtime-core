from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True)
class DeleteCategoryCommand:
    tenant_id: EntityIdVO
    category_id: CategoryIdVO
