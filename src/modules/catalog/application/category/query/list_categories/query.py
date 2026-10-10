from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListCategoriesQuery:
    """Явное чтение list_categories в доверенном tenant."""

    tenant_id: EntityIdVO
    locale: str
    search: str = ""
    page: int = 1
    page_size: int = 20

    parent_id: CategoryIdVO | None = None
    roots_only: bool = False
