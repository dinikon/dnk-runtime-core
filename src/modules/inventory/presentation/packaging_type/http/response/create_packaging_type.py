from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.packaging_type.command.create_packaging_type.dto import (
    CreatePackagingTypeResultDTO,
)


class CreatePackagingTypeResponse(BaseModel):
    """Описывает отдельный HTTP-результат сценария Create типа тары."""

    id: UUID
    code: str
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, dto: CreatePackagingTypeResultDTO) -> Self:
        """Явно преобразует результат Application в HTTP-представление."""
        return cls(id=dto.id, code=dto.code, name=dto.name, is_active=dto.is_active)
