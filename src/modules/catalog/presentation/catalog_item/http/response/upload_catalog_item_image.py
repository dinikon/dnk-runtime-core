from pydantic import BaseModel
from uuid import UUID


class UploadCatalogItemImageResponse(BaseModel):
    """Отдельный HTTP-результат сценария upload_catalog_item_image."""

    id: UUID
    revision: int
    image_id: UUID
    file_id: UUID
