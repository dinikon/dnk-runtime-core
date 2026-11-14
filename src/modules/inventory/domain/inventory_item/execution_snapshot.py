from dataclasses import dataclass

from src.modules.inventory.domain.policy.inventory_tracking import (
    InventoryTrackingPolicy,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemExecutionSnapshotError,
)
from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
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
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class InventoryItemExecutionSnapshot:
    """Передаёт настройки количества, прослеживаемости и дат без карточки товара и коллекций."""

    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity_rules: QuantityRulesVO
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode

    def ensure_valid(self) -> None:
        """Проверяет собственные типы и совместимость правил серий и обязательного срока."""
        if (
            not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity_rules, QuantityRulesVO)
            or not isinstance(self.tracking_mode, TrackingMode)
            or not isinstance(self.expiration_mode, ExpirationMode)
        ):
            raise InvalidInventoryItemExecutionSnapshotError(
                "Нужен типизированный снимок правил исполнения товара."
            )
        InventoryItemStockSnapshot(
            self.inventory_item_id,
            self.base_uom,
            self.quantity_rules,
            self.tracking_mode,
        ).ensure_valid()
        InventoryTrackingPolicy.ensure_compatible(
            tracking_mode=self.tracking_mode, expiration_mode=self.expiration_mode
        )

    def stock_snapshot(self) -> InventoryItemStockSnapshot:
        """Предоставляет минимальный существующий контракт проверки физических измерений."""
        self.ensure_valid()
        return InventoryItemStockSnapshot(
            self.inventory_item_id,
            self.base_uom,
            self.quantity_rules,
            self.tracking_mode,
        )

    def tracking_snapshot(self) -> InventoryItemTrackingSnapshot:
        """Предоставляет настройки прослеживаемости и контроля срока партии."""
        self.ensure_valid()
        return InventoryItemTrackingSnapshot(
            self.inventory_item_id, self.tracking_mode, self.expiration_mode
        )
