from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
)
from src.modules.inventory.domain.policy.inventory_tracking import (
    InventoryTrackingPolicy,
)
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

    def ensure_valid(self) -> None:
        """Проверяет идентичность и совместимость настроек прослеживаемости и срока."""
        if not isinstance(self.inventory_item_id, InventoryItemIdVO):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Нужен типизированный ID товара."
            )
        InventoryTrackingPolicy.ensure_compatible(
            tracking_mode=self.tracking_mode, expiration_mode=self.expiration_mode
        )
