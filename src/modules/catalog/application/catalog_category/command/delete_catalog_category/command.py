from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteCatalogCategoryCommand:
    """Идентификатор категории для удаления."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    category_id: CatalogCategoryIdVO
