from uuid import UUID
from pydantic import BaseModel


class SetCatalogVariantSkuResponse(BaseModel):
    """Возвращает собственную складскую ссылку конкретного варианта."""

    item_id: UUID
    inventory_item_id: UUID | None
    sku: str | None
    inventory_item_created: bool
