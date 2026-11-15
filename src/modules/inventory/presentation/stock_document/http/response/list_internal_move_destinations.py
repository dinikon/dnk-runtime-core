from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.dto import (
    ListInternalMoveDestinationsResultDTO,
)


class InternalMoveDestinationResponse(BaseModel):
    """Сериализует собственный контракт адреса назначения."""

    id: UUID
    code: str
    name: str


class ListInternalMoveDestinationsResponse(BaseModel):
    """Возвращает страницу допустимых адресов конкретного склада."""

    items: list[InternalMoveDestinationResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(
        cls, dto: ListInternalMoveDestinationsResultDTO
    ) -> "ListInternalMoveDestinationsResponse":
        """Явно преобразует результат собственного сценария чтения."""
        return cls(
            items=[
                InternalMoveDestinationResponse(id=v.id, code=v.code, name=v.name)
                for v in dto.items
            ],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
