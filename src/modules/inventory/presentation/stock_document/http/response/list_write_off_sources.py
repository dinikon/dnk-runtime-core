from datetime import date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.list_write_off_sources.dto import (
    ListWriteOffSourcesResultDTO,
)


class WriteOffSourceItemResponse(BaseModel):
    """Сериализует текущие физические измерения и точное количество источника."""

    id: UUID
    inventory_item_id: UUID
    location_id: UUID
    location_code: str
    stock_status: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    manufactured_on: date | None
    expires_on: date | None
    base_uom: str
    on_hand_quantity: Decimal
    version: int


class ListWriteOffSourcesResponse(BaseModel):
    """Возвращает страницу источников с собственным HTTP-контрактом."""

    items: list[WriteOffSourceItemResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(
        cls, dto: ListWriteOffSourcesResultDTO
    ) -> "ListWriteOffSourcesResponse":
        """Явно преобразует проекцию без плавающих чисел."""
        return cls(
            items=[
                WriteOffSourceItemResponse(
                    id=v.id,
                    inventory_item_id=v.inventory_item_id,
                    location_id=v.location_id,
                    location_code=v.location_code,
                    stock_status=v.stock_status,
                    lot_id=v.lot_id,
                    lot_number=v.lot_number,
                    serial_id=v.serial_id,
                    serial_number=v.serial_number,
                    manufactured_on=v.manufactured_on,
                    expires_on=v.expires_on,
                    base_uom=v.base_uom,
                    on_hand_quantity=v.on_hand_quantity,
                    version=v.version,
                )
                for v in dto.items
            ],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
