from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemPrimaryImageResultDTO:
    """Результат сценария set_catalog_item_primary_image: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
