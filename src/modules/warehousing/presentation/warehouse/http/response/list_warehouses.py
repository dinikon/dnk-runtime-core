from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.warehousing.application.warehouse.query.list_warehouses.dto import (
    ListWarehousesResultDTO,
)


class ListWarehouseItemResponse(BaseModel):
    """Строка HTTP-списка складов, независимая от карточки."""

    id: UUID
    code: str
    title: str
    type: str
    status: str
    revision: int


class ListWarehousesResponse(BaseModel):
    """Страница HTTP-списка с необязательным курсором продолжения."""

    items: list[ListWarehouseItemResponse]
    next_cursor: str | None

    @classmethod
    def from_dto(cls, dto: ListWarehousesResultDTO) -> Self:
        """Явно преобразует DTO списка и его строки."""
        return cls(
            items=[
                ListWarehouseItemResponse(
                    id=item.id,
                    code=item.code,
                    title=item.title,
                    type=item.type,
                    status=item.status,
                    revision=item.revision,
                )
                for item in dto.items
            ],
            next_cursor=dto.next_cursor,
        )
