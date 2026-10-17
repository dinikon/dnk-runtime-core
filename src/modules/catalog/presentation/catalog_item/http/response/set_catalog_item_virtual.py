from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemVirtualResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_virtual."""

    id: UUID
    revision: int
