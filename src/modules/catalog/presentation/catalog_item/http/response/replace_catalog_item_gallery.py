from pydantic import BaseModel
from uuid import UUID


class ReplaceCatalogItemGalleryResponse(BaseModel):
    """HTTP результат отдельного сценария replace_catalog_item_gallery."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
