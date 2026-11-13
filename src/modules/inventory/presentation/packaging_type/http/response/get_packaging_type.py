from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)


class GetPackagingTypeResponse(BaseModel):
    """Описывает отдельный HTTP-результат сценария Get типа тары."""

    id: UUID
    code: str
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, dto: GetPackagingTypeResultDTO) -> Self:
        """Явно преобразует результат Application в HTTP-представление."""
        return cls(id=dto.id, code=dto.code, name=dto.name, is_active=dto.is_active)
