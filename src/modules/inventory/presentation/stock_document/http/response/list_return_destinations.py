from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.list_return_destinations.dto import (
    ListReturnDestinationsResultDTO,
)


class ReturnDestinationResponse(BaseModel):
    """Сериализует собственный контракт адреса назначения."""

    id: UUID
    code: str
    name: str


class ListReturnDestinationsResponse(BaseModel):
    """Возвращает страницу допустимых адресов конкретного склада."""

    items: list[ReturnDestinationResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(
        cls, dto: ListReturnDestinationsResultDTO
    ) -> "ListReturnDestinationsResponse":
        """Явно преобразует результат собственного сценария чтения."""
        return cls(
            items=[
                ReturnDestinationResponse(id=v.id, code=v.code, name=v.name)
                for v in dto.items
            ],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
