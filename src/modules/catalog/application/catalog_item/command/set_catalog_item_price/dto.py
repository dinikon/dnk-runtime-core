from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemPriceResultDTO:
    """Результат сценария set_catalog_item_price: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
