from uuid import UUID
from pydantic import BaseModel


class SetCatalogItemSkuResponse(BaseModel):
    """Возвращает актуальную ссылку корня и факт создания InventoryItem."""

    item_id: UUID
    inventory_item_id: UUID | None
    sku: str | None
    inventory_item_created: bool
