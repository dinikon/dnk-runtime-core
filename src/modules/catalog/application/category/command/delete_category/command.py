from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True, slots=True)
class DeleteCategoryCommand:
    """Вход сценария delete_category с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    category_id: CategoryIdVO
    expected_revision: int
