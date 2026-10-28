from dataclasses import dataclass
from datetime import datetime
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemDetailsDTO,
)


@dataclass(frozen=True, slots=True)
class GetCatalogProductSnapshotResultDTO:
    """Публичный результат конкретного read-сценария Catalog."""

    root: CatalogItemDetailsDTO
    variants: tuple[CatalogItemDetailsDTO, ...]
    locale: str
    as_of: datetime
