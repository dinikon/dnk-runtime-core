from dataclasses import dataclass

from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class UpdateCategoryCommand:
    """Команда application-слоя на обновление категории товаров tenant."""

    tenant_id: EntityIdVO
    category_id: CategoryIdVO
    name: str
    parent_category_id: CategoryIdVO | None = None
