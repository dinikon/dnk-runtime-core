from dataclasses import dataclass

from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListProductsQuery:
    """Query application-слоя на список товаров tenant с пагинацией."""

    tenant_id: EntityIdVO
    limit: int
    offset: int
    category_id: CategoryIdVO | None = None
