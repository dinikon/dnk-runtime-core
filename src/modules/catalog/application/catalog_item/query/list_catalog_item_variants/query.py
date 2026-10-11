from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ListCatalogItemVariantsQuery:
    """Явный вход read сценария list_catalog_item_variants."""

    tenant_id: EntityIdVO
    root_id: CatalogItemIdVO
    locale: str
    offset: int = 0
    limit: int = 50
    as_of: datetime | None = None
