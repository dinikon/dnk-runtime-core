from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteCatalogItemCommand:
    """Удаление корня с проверкой его ревизии."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_root_revision: int
    discarded_ids: frozenset[CatalogItemIdVO] = frozenset()
