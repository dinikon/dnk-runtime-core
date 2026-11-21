from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


@dataclass(frozen=True, slots=True)
class UpdatedInventoryItemBarcodeDTO:
    """Передаёт сохранённую идентичность и код штрихкода после изменения."""

    id: UUID
    barcode: str


@dataclass(frozen=True, slots=True)
class UpdateInventoryItemResultDTO:
    """Описывает актуальные данные после сценария обновления."""

    id: UUID
    sku: str
    base_uom: str
    quantity_step: Decimal
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: tuple[UpdatedInventoryItemBarcodeDTO, ...]
