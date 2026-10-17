from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemCategoriesResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_categories."""

    id: UUID
    revision: int
