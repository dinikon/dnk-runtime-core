from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemPrimaryImageResponse(BaseModel):
    """HTTP результат отдельного сценария set_catalog_item_primary_image."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
