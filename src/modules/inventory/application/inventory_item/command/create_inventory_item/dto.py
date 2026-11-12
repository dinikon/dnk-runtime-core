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
class CreatedInventoryItemBarcodeDTO:
    """Передаёт идентичность и значение созданного штрихкода."""

    id: UUID
    barcode: str


@dataclass(frozen=True, slots=True)
class CreateInventoryItemResultDTO:
    """Описывает созданную позицию до завершения внешнего UoW."""

    id: UUID
    sku: str
    base_uom: str
    quantity_step: Decimal
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: tuple[CreatedInventoryItemBarcodeDTO, ...]
