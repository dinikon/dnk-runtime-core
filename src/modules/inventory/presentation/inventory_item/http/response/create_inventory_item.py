from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.inventory_item.command.create_inventory_item.dto import (
    CreateInventoryItemResultDTO,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class CreateInventoryItemQuantityRulesResponse(BaseModel):
    """Возвращает шаг созданной позиции как точную десятичную строку."""

    step: Decimal


class CreateInventoryItemBarcodeResponse(BaseModel):
    """Возвращает созданный штрихкод и выданный сервером UUID."""

    id: UUID
    barcode: str


class CreateInventoryItemResponse(BaseModel):
    """Описывает HTTP-результат создания позиции."""

    id: UUID
    sku: str
    base_uom: str
    quantity_rules: CreateInventoryItemQuantityRulesResponse
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: tuple[CreateInventoryItemBarcodeResponse, ...]

    @classmethod
    def from_dto(cls, dto: CreateInventoryItemResultDTO) -> Self:
        """Явно переводит результат Application в контракт POST."""
        return cls(
            id=dto.id,
            sku=dto.sku,
            base_uom=dto.base_uom,
            quantity_rules=CreateInventoryItemQuantityRulesResponse(
                step=dto.quantity_step
            ),
            tracking_mode=dto.tracking_mode,
            expiration_mode=dto.expiration_mode,
            barcodes=tuple(
                CreateInventoryItemBarcodeResponse(
                    id=barcode.id, barcode=barcode.barcode
                )
                for barcode in dto.barcodes
            ),
        )
