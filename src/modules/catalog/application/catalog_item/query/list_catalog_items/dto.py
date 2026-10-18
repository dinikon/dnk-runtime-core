from dataclasses import dataclass
from datetime import datetime
from src.modules.catalog.application.catalog_item.query.list_catalog_items.row_dto import (
    CatalogItemListRowDTO,
)


@dataclass(frozen=True, slots=True)
class ListCatalogItemsResultDTO:
    """Конкретный результат сценария list_catalog_items."""

    items: tuple[CatalogItemListRowDTO, ...]
    total: int
    offset: int
    limit: int
    as_of: datetime
