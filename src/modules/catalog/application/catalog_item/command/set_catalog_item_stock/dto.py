from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemStockResultDTO:
    """Результат сценария set_catalog_item_stock: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
