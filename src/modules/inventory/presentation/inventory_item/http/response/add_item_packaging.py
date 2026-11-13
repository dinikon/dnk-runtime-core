from decimal import Decimal
from typing import Self
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.inventory_item.command.add_item_packaging.dto import (
    AddItemPackagingResultDTO,
)


class AddItemPackagingResponse(BaseModel):
    """Сериализует результат сценария упаковки с количеством строкой Decimal."""

    id: UUID
    inventory_item_id: UUID
    packaging_type_id: UUID
    code: str
    name: str
    content_quantity: Decimal
    content_uom: str

    @classmethod
    def from_dto(cls, dto: AddItemPackagingResultDTO) -> Self:
        """Явно преобразует контракт Application в отдельный HTTP-ответ."""
        return cls(
            id=dto.id,
            inventory_item_id=dto.inventory_item_id,
            packaging_type_id=dto.packaging_type_id,
            code=dto.code,
            name=dto.name,
            content_quantity=dto.content_quantity,
            content_uom=dto.content_uom,
        )
