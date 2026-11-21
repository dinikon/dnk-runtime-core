from decimal import Decimal
from typing import Self
from uuid import UUID
from pydantic import BaseModel

from src.modules.inventory.application.inventory_item.command.update_inventory_item.dto import (
    UpdateInventoryItemResultDTO,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class PutInventoryItemQuantityRulesResponse(BaseModel):
    """Возвращает точный десятичный шаг количества."""

    step: Decimal


class PutInventoryItemBarcodeResponse(BaseModel):
    """Возвращает код и сохранённый либо новый ID штрихкода."""

    id: UUID
    barcode: str


class PutInventoryItemResponse(BaseModel):
    """Описывает отдельный HTTP-результат PUT."""

    id: UUID
    sku: str
    base_uom: str
    quantity_rules: PutInventoryItemQuantityRulesResponse
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: tuple[PutInventoryItemBarcodeResponse, ...]

    @classmethod
    def from_dto(cls, dto: UpdateInventoryItemResultDTO) -> Self:
        """Явно переводит результат обновления в контракт PUT."""
        return cls(
            id=dto.id,
            sku=dto.sku,
            base_uom=dto.base_uom,
            quantity_rules=PutInventoryItemQuantityRulesResponse(
                step=dto.quantity_step
            ),
            tracking_mode=dto.tracking_mode,
            expiration_mode=dto.expiration_mode,
            barcodes=tuple(
                PutInventoryItemBarcodeResponse(id=child.id, barcode=child.barcode)
                for child in dto.barcodes
            ),
        )
