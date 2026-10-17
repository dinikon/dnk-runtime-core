from dataclasses import dataclass
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class SetCatalogItemCategoriesCommand:
    """Явный вход сценария set_catalog_item_categories в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_revision: int
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
