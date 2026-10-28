from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogVariantValues,
)


@dataclass(frozen=True, slots=True)
class CreateCatalogVariantCommand:
    """Доверенный контекст изменения entity внутри родительского агрегата."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    product: CreateCatalogVariantValues
