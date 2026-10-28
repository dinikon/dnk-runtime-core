from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UploadCatalogVariantImageResultDTO:
    """Результат сценария upload_catalog_item_image: идентичности товара, изображения и файла."""

    id: UUID

    image_id: UUID
    file_id: UUID
