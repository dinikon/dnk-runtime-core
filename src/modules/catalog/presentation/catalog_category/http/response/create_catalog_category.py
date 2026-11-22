from uuid import UUID
from pydantic import BaseModel


class CreateCatalogCategoryResponse(BaseModel):
    """Возвращает идентификатор созданного узла."""

    id: UUID
