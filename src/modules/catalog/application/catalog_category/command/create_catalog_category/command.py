from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO


@dataclass(frozen=True, slots=True)
class CreateCatalogCategoryCommand:
    """Первое название, его локаль и родитель нового узла."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    parent_id: CatalogCategoryIdVO | None
    locale: LocaleVO
    name: str
