from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)


@dataclass(frozen=True, slots=True)
class UpdateCatalogCategoryCommand:
    """Изменения положения в дереве и названий по языкам."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    category_id: CatalogCategoryIdVO
    move: bool
    parent_id: CatalogCategoryIdVO | None
    translations: dict[str, str]
