from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemStockResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_stock."""

    id: UUID
    revision: int
