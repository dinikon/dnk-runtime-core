from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.warehouse.command.set_default_storage_location.dto import (
    SetDefaultStorageLocationResultDTO,
)


class SetDefaultStorageLocationResponse(BaseModel):
    """Описывает отдельный HTTP-результат назначения основной STORAGE-локации."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID

    @classmethod
    def from_dto(cls, dto: SetDefaultStorageLocationResultDTO) -> Self:
        """Явно преобразует результат Application в карточку склада."""
        return cls(
            id=dto.id,
            code=dto.code,
            name=dto.name,
            is_active=dto.is_active,
            default_storage_location_id=dto.default_storage_location_id,
        )
