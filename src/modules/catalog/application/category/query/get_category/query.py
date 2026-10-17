from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True, slots=True)
class GetCategoryQuery:
    """Явное чтение get_category в доверенном tenant."""

    tenant_id: EntityIdVO
    category_id: CategoryIdVO
    locale: str
