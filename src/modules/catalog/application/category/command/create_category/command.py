from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True, slots=True)
class CreateCategoryCommand:
    """Вход создания category с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    locale: str
    label: str
    parent_id: CategoryIdVO | None = None
