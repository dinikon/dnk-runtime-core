from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemMetadataResultDTO:
    """Результат сценария set_catalog_item_metadata: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
