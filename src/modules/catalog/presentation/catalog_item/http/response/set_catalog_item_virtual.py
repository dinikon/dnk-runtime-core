from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemVirtualResponse(BaseModel):
    """HTTP результат отдельного сценария set_catalog_item_virtual."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
