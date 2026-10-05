from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.category.query.list_categories.dto import (
    CategoryListItemDTO,
)


class ListCategoryResponse(BaseModel):
    id: UUID
    parent_id: UUID | None
    name: str | None

    @classmethod
    def from_dto(cls, dto: CategoryListItemDTO) -> "ListCategoryResponse":
        return cls(id=dto.id, parent_id=dto.parent_id, name=dto.name)
