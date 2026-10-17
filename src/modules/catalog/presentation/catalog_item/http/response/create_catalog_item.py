from pydantic import BaseModel
from uuid import UUID


class CreateCatalogItemResponse(BaseModel):
    """Отдельный HTTP-результат сценария create_catalog_item."""

    id: UUID
