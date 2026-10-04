from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.sku.command.create_sku.dto import (
    CreateSkuResultDTO,
)


class CreateSkuResponse(BaseModel):
    """HTTP-представление SKU для сценария create_sku."""

    id: UUID
    code: str
    title: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: CreateSkuResultDTO) -> "CreateSkuResponse":
        """Явно преобразует application DTO в транспортную схему."""
        return cls(
            id=dto.id,
            code=dto.code,
            title=dto.title,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
