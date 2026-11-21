from decimal import Decimal
from typing import Self
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.inventory_item.query.list_item_packagings.dto import (
    ListItemPackagingsResultDTO,
)


class ListItemPackagingResponse(BaseModel):
    """Описывает строку HTTP-списка вариантов упаковки."""

    id: UUID
    inventory_item_id: UUID
    packaging_type_id: UUID
    code: str
    name: str
    content_quantity: Decimal
    content_uom: str


class ListItemPackagingsResponse(BaseModel):
    """Описывает страницу вариантов упаковки и параметры серверной пагинации."""

    items: tuple[ListItemPackagingResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListItemPackagingsResultDTO) -> Self:
        """Явно преобразует каждую строку проекции и metadata страницы."""
        return cls(
            items=tuple(
                ListItemPackagingResponse(
                    id=row.id,
                    inventory_item_id=row.inventory_item_id,
                    packaging_type_id=row.packaging_type_id,
                    code=row.code,
                    name=row.name,
                    content_quantity=row.content_quantity,
                    content_uom=row.content_uom,
                )
                for row in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
