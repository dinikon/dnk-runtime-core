from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class LockCatalogItemForBindingCommand:
    """Задаёт типизированный вход сценария lock_catalog_item_for_binding."""

    tenant_id: EntityIdVO
    item_id: CatalogItemIdVO
