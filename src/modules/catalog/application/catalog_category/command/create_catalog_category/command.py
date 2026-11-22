from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO


@dataclass(frozen=True, slots=True)
class CreateCatalogCategoryCommand:
    """Название, исходный язык и родитель нового узла."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    parent_id: CatalogCategoryIdVO | None
    source_locale: LocaleVO
    name: str
