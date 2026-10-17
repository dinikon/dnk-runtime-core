from pydantic import BaseModel
from uuid import UUID


class CreateSimpleCatalogItemResponse(BaseModel):
    """Отдельный HTTP-результат сценария create_simple_catalog_item."""

    id: UUID
    revision: int
