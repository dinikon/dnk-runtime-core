from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemSkuResponse(BaseModel):
    """HTTP результат отдельного сценария set_catalog_item_sku."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
