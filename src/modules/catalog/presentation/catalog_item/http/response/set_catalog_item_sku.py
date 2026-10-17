from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemSkuResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_sku."""

    id: UUID
    revision: int
