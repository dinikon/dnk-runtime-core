from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(frozen=True, slots=True)
class MoveCategoryCommand:
    """Явное перемещение категории в актуальном дереве."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    category_id: CategoryIdVO

    parent_id: CategoryIdVO | None
