from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    ListPackagingTypesResultDTO,
)


class PackagingTypeListItemResponse(BaseModel):
    """Описывает строку HTTP-списка типов тары."""

    id: UUID
    code: str
    name: str
    is_active: bool


class ListPackagingTypesResponse(BaseModel):
    """Передаёт HTTP-страницу и параметры пагинации справочника."""

    items: tuple[PackagingTypeListItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListPackagingTypesResultDTO) -> Self:
        """Явно преобразует строки списка и общее число по фильтрам."""
        return cls(
            items=tuple(
                PackagingTypeListItemResponse(
                    id=item.id, code=item.code, name=item.name, is_active=item.is_active
                )
                for item in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
