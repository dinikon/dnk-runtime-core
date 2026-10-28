from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class ListCatalogVariantsQuery:
    """Доверенный контекст чтения принадлежащих родителю позиций."""

    tenant_id: EntityIdVO
    item_id: CatalogItemIdVO
    locale: str
    as_of: datetime | None = None
    offset: int = 0
    limit: int = 25
