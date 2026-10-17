from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemStatusResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_status."""

    id: UUID
    revision: int
