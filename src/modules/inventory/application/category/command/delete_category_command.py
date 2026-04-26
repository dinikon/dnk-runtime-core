from dataclasses import dataclass

from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteCategoryCommand:
    """Команда application-слоя на удаление категории товаров tenant."""

    tenant_id: EntityIdVO
    category_id: CategoryIdVO
