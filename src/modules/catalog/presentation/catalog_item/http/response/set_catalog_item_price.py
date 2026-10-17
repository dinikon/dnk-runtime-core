from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemPriceResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_price."""

    id: UUID
    revision: int
