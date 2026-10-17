from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemAttributesResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_attributes."""

    id: UUID
    revision: int
