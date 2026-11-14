from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.stock_lot.command.create_stock_lot.dto import (
    CreateStockLotResultDTO,
)


class CreateStockLotResponse(BaseModel):
    """Сериализует результат собственного HTTP-сценария партии."""

    id: UUID
    inventory_item_id: UUID
    number: str
    manufactured_on: date | None
    expires_on: date | None

    @classmethod
    def from_dto(cls, dto: CreateStockLotResultDTO) -> Self:
        """Явно переносит поля результата, сохраняя date и исходный номер."""
        return cls(
            id=dto.id,
            inventory_item_id=dto.inventory_item_id,
            number=dto.number,
            manufactured_on=dto.manufactured_on,
            expires_on=dto.expires_on,
        )
