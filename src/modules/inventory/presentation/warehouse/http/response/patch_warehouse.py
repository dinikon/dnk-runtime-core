from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.warehouse.command.update_warehouse.dto import (
    UpdateWarehouseResultDTO,
)


class PatchWarehouseResponse(BaseModel):
    """Описывает отдельный HTTP-контракт результата PATCH склада."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID | None

    @classmethod
    def from_dto(cls, dto: UpdateWarehouseResultDTO) -> Self:
        """Явно сериализует итог Application, сохраняя основную ссылку."""
        return cls(
            id=dto.id,
            code=dto.code,
            name=dto.name,
            is_active=dto.is_active,
            default_storage_location_id=dto.default_storage_location_id,
        )
