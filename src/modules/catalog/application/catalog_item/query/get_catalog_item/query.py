from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GetCatalogItemQuery:
    """Явный вход read сценария get_catalog_item."""

    tenant_id: EntityIdVO
    item_id: CatalogItemIdVO
    locale: str
    as_of: datetime | None = None
