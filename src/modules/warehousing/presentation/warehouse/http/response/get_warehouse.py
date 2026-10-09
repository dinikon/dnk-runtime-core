from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.warehousing.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseDetailsDTO,
)


class GetWarehousePolicyResponse(BaseModel):
    """Настройки в самостоятельном HTTP-контракте карточки склада."""

    timezone: str


class GetWarehouseResponse(BaseModel):
    """Полная HTTP-карточка склада с политикой и аудитом."""

    id: UUID
    code: str
    title: str
    type: str
    status: str
    policy: GetWarehousePolicyResponse
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: GetWarehouseDetailsDTO) -> Self:
        """Собирает ответ карточки из её собственного DTO."""
        return cls(
            id=dto.id,
            code=dto.code,
            title=dto.title,
            type=dto.type,
            status=dto.status,
            policy=GetWarehousePolicyResponse(timezone=dto.policy.timezone),
            revision=dto.revision,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
