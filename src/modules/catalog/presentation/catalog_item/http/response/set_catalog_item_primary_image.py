from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemPrimaryImageResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_primary_image."""

    id: UUID
    revision: int
