from dataclasses import dataclass
from datetime import datetime
from src.modules.catalog.application.catalog_item.read_dto import CatalogItemReadDTO


@dataclass(frozen=True, slots=True)
class GetCatalogItemResultDTO:
    """Конкретный результат сценария get_catalog_item."""

    item: CatalogItemReadDTO
    as_of: datetime
