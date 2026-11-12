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
class InventoryItemListItemDTO:
    """Описывает строку списка без дочерних коллекций и восстановления Domain."""

    id: UUID
    sku: str
    base_uom: str
    quantity_step: Decimal
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode


@dataclass(frozen=True, slots=True)
class ListInventoryItemsResultDTO:
    """Передаёт страницу позиций и размер отфильтрованного списка."""

    items: tuple[InventoryItemListItemDTO, ...]
    total: int
    offset: int
    limit: int
