from dataclasses import dataclass
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from datetime import datetime
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)


@dataclass(frozen=True, slots=True)
class ListCatalogItemsQuery:
    """Явный вход read сценария list_catalog_items."""

    tenant_id: EntityIdVO
    locale: str
    status: CatalogItemStatus | None = None
    search: str | None = None
    offset: int = 0
    limit: int = 50
    as_of: datetime | None = None
