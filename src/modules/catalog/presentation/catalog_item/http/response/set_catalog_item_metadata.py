from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemMetadataResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_metadata."""

    id: UUID
    revision: int
