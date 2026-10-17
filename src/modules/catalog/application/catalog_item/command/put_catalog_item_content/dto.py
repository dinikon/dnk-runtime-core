from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutCatalogItemContentResultDTO:
    """Результат сценария put_catalog_item_content: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
