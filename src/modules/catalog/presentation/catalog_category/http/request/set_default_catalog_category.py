from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SetDefaultCatalogCategoryRequest(BaseModel):
    """Выбор категории для следующих новых товаров."""

    model_config = ConfigDict(extra="forbid")
    category_id: UUID
