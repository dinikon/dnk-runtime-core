from dataclasses import dataclass
from datetime import datetime

from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class CatalogStockChanged:
    """Количественные настройки семьи действительно изменились."""

    item_id: CatalogItemIdVO
    occurred_at: datetime
    position_ids: tuple[CatalogItemIdVO, ...]
