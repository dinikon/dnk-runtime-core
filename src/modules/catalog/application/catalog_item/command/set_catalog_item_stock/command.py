from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)


@dataclass(frozen=True, slots=True)
class SetCatalogItemStockCommand:
    """Явный вход сценария set_catalog_item_stock в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_revision: int
    stock: StockSpecificationVO
