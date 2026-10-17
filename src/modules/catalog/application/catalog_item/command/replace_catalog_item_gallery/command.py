from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery


@dataclass(frozen=True, slots=True)
class ReplaceCatalogItemGalleryCommand:
    """Явный вход сценария replace_catalog_item_gallery в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_revision: int
    locale: str
    gallery: CatalogItemGallery
