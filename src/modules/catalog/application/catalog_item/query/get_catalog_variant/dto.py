from dataclasses import dataclass
from datetime import datetime
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemDetailsDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.row_dto import (
    CatalogItemListRowDTO,
)


@dataclass(frozen=True, slots=True)
class GetCatalogVariantResultDTO:
    """Публичный результат конкретного read-сценария Catalog."""

    item: CatalogItemDetailsDTO
    as_of: datetime
