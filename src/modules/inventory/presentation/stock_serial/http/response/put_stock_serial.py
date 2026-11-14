from datetime import date
from typing import Self, Literal
from uuid import UUID
from pydantic import BaseModel

from src.modules.inventory.application.stock_serial.command.update_stock_serial.dto import (
    UpdateStockSerialResultDTO,
)


class PutStockSerialResponse(BaseModel):
    """Сериализует результат собственного HTTP-сценария экземпляра."""

    id: UUID
    inventory_item_id: UUID
    number: str
    lot_id: UUID | None
    lot_number: str | None
    date_source: Literal["NONE", "LOT"]
    manufactured_on: date | None
    expires_on: date | None

    @classmethod
    def from_dto(cls, dto: UpdateStockSerialResultDTO) -> Self:
        """Явно переносит поля результата, сохраняя date и исходный номер."""
        return cls(
            id=dto.id,
            inventory_item_id=dto.inventory_item_id,
            number=dto.number,
            lot_id=dto.lot_id,
            lot_number=dto.lot_number,
            date_source=dto.date_source,
            manufactured_on=dto.manufactured_on,
            expires_on=dto.expires_on,
        )
