from dataclasses import dataclass
from datetime import datetime
from src.modules.catalog.application.catalog_item.read_dto import CatalogItemReadDTO


@dataclass(frozen=True, slots=True)
class ListCatalogItemVariantsResultDTO:
    """Конкретный результат сценария list_catalog_item_variants."""

    items: tuple[CatalogItemReadDTO, ...]
    total: int
    offset: int
    limit: int
    as_of: datetime
