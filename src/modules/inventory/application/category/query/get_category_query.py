from dataclasses import dataclass

from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetCategoryQuery:
    """Query application-слоя на получение одной категории tenant."""

    tenant_id: EntityIdVO
    category_id: CategoryIdVO
