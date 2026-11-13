from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.packaging_type.command.update_packaging_type.dto import (
    UpdatePackagingTypeResultDTO,
)


class PutPackagingTypeResponse(BaseModel):
    """Описывает отдельный HTTP-контракт результата PUT типа тары."""

    id: UUID
    code: str
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, dto: UpdatePackagingTypeResultDTO) -> Self:
        """Явно преобразует результат Application без представлений хранения."""
        return cls(id=dto.id, code=dto.code, name=dto.name, is_active=dto.is_active)
