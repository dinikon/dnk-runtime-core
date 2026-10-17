from pydantic import BaseModel
from uuid import UUID


class PutCatalogItemContentResponse(BaseModel):
    """Отдельный HTTP-результат сценария put_catalog_item_content."""

    id: UUID
    revision: int
