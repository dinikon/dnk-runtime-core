from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.category.query.get_category.dto import (
    CategoryDetailsDTO,
    CategoryTranslationDTO,
)


class CategoryTranslationResponse(BaseModel):
    locale: str
    name: str

    @classmethod
    def from_dto(cls, dto: CategoryTranslationDTO) -> "CategoryTranslationResponse":
        return cls(locale=dto.locale, name=dto.name)


class GetCategoryResponse(BaseModel):
    id: UUID
    parent_id: UUID | None
    requested_locale: str
    name: str | None
    translations: list[CategoryTranslationResponse]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: CategoryDetailsDTO) -> "GetCategoryResponse":
        return cls(
            id=dto.id,
            parent_id=dto.parent_id,
            requested_locale=dto.requested_locale,
            name=dto.name,
            translations=[
                CategoryTranslationResponse.from_dto(item) for item in dto.translations
            ],
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
