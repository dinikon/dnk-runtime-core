from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class UploadCatalogItemImageCommand:
    """Поток raster изображения и конкретное назначение в локализованной галерее."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO

    locale: str
    source: BinaryIO
    size_bytes: int
    name: str
    content_type: str
    main: bool = False
    alt: str = ""
    caption: str = ""
