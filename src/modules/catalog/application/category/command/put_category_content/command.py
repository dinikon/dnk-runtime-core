from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True, slots=True)
class PutCategoryContentCommand:
    """Вход сценария put_category_content с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    category_id: CategoryIdVO
    expected_revision: int
    locale: str
    label: str
