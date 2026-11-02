from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


@dataclass(frozen=True, slots=True)
class InventoryItemTrackingSnapshot:
    """Неизменяемые настройки товара для проверки прослеживаемости без чужого агрегата."""

    inventory_item_id: InventoryItemIdVO
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
