from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemSkuResultDTO:
    """Результат сценария set_catalog_item_sku: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
