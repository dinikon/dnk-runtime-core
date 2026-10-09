from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.warehousing.application.warehouse.command.create_warehouse.dto import (
    CreateWarehouseResultDTO,
)


class CreateWarehouseResponse(BaseModel):
    """HTTP-результат POST создания склада."""

    id: UUID
    code: str
    status: str
    revision: int

    @classmethod
    def from_dto(cls, dto: CreateWarehouseResultDTO) -> Self:
        """Явно преобразует DTO только сценария создания."""
        return cls(id=dto.id, code=dto.code, status=dto.status, revision=dto.revision)
