from uuid import UUID
from pydantic import BaseModel


class UpdateCatalogCategoryResponse(BaseModel):
    """Возвращает идентификатор обновлённой категории."""

    id: UUID
