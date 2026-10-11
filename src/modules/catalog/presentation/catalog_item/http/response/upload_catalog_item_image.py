from pydantic import BaseModel
from uuid import UUID


class UploadCatalogItemImageResponse(BaseModel):
    """HTTP результат отдельного сценария upload_catalog_item_image."""

    item_id: UUID
    root_id: UUID
    image_id: UUID
    file_id: UUID
    revision: int
    root_revision: int
