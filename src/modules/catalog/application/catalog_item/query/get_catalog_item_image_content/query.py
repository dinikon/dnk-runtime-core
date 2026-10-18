from dataclasses import dataclass
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class GetCatalogItemImageContentQuery:
    """Изображение эффективной галереи выбранной locale."""

    tenant_id: EntityIdVO
    item_id: CatalogItemIdVO
    locale: str
    image_id: UUID
