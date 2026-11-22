from uuid import UUID
from pydantic import BaseModel


class SetDefaultCatalogCategoryResponse(BaseModel):
    """Возвращает идентификатор новой категории по умолчанию."""

    id: UUID
