from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReplaceCatalogItemGalleryResultDTO:
    """Результат сценария replace_catalog_item_gallery: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
