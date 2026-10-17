from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UploadCatalogItemImageResultDTO:
    """Результат сценария upload_catalog_item_image: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
    image_id: UUID
    file_id: UUID
