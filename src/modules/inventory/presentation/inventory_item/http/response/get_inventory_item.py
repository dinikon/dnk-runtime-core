from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemResultDTO,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class GetInventoryItemQuantityRulesResponse(BaseModel):
    """Сериализует точный шаг количества строкой Decimal."""

    step: Decimal


class GetInventoryItemBarcodeResponse(BaseModel):
    """Передаёт идентификатор и код сохранённого штрихкода."""

    id: UUID
    barcode: str


class GetInventoryItemResponse(BaseModel):
    """Описывает результат чтения карточки складской позиции."""

    id: UUID
    sku: str
    base_uom: str
    quantity_rules: GetInventoryItemQuantityRulesResponse
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: tuple[GetInventoryItemBarcodeResponse, ...]

    @classmethod
    def from_dto(cls, dto: GetInventoryItemResultDTO) -> Self:
        """Явно переводит проекцию карточки в контракт GET."""
        return cls(
            id=dto.id,
            sku=dto.sku,
            base_uom=dto.base_uom,
            quantity_rules=GetInventoryItemQuantityRulesResponse(
                step=dto.quantity_step
            ),
            tracking_mode=dto.tracking_mode,
            expiration_mode=dto.expiration_mode,
            barcodes=tuple(
                GetInventoryItemBarcodeResponse(id=child.id, barcode=child.barcode)
                for child in dto.barcodes
            ),
        )
