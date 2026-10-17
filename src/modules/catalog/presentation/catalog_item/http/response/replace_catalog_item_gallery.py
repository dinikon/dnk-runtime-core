from pydantic import BaseModel
from uuid import UUID


class ReplaceCatalogItemGalleryResponse(BaseModel):
    """Отдельный HTTP-результат сценария replace_catalog_item_gallery."""

    id: UUID
    revision: int
