from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemTagsResultDTO:
    """Результат сценария set_catalog_item_tags: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
