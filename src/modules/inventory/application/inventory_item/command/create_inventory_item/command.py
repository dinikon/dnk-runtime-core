from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


@dataclass(frozen=True, slots=True)
class CreateInventoryItemCommand:
    """Передаёт SKU и необязательные настройки; defaults выбирает фабрика Domain."""

    sku: str
    base_uom: str | None = None
    quantity_step: Decimal | None = None
    tracking_mode: TrackingMode | None = None
    expiration_mode: ExpirationMode | None = None
    barcodes: tuple[str, ...] = ()
