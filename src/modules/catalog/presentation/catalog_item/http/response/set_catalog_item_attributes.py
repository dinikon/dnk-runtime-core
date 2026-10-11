from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemAttributesResponse(BaseModel):
    """HTTP результат отдельного сценария set_catalog_item_attributes."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
