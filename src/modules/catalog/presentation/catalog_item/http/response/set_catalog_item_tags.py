from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemTagsResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_tags."""

    id: UUID
    revision: int
