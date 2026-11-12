from dataclasses import dataclass

from src.modules.catalog.application.catalog_item.inventory_item_selection import (
    CatalogInventoryItemSelection,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class SetCatalogItemSkuCommand:
    """Назначает SKU конкретному узлу через корень его агрегата."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    selection: CatalogInventoryItemSelection
    variant_id: CatalogItemIdVO | None = None
