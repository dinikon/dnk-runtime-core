from decimal import Decimal
from typing import Self
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.inventory_item.command.update_item_packaging.dto import (
    UpdateItemPackagingResultDTO,
)


class PatchItemPackagingResponse(BaseModel):
    """Сериализует результат PATCH упаковки с точным количеством строкой Decimal."""

    id: UUID
    inventory_item_id: UUID
    packaging_type_id: UUID
    code: str
    name: str
    content_quantity: Decimal
    content_uom: str

    @classmethod
    def from_dto(cls, dto: UpdateItemPackagingResultDTO) -> Self:
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
