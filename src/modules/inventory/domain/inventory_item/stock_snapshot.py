from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class InventoryItemStockSnapshot:
    """Неизменяемые настройки количества и прослеживаемости для физического учёта."""

    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity_rules: QuantityRulesVO
    tracking_mode: TrackingMode

    def ensure_valid(self) -> None:
        """Проверяет типы, известную единицу и согласованность серийного учёта."""
        if (
            not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity_rules, QuantityRulesVO)
            or not isinstance(self.tracking_mode, TrackingMode)
        ):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен типизированный учётный снимок товара."
            )
        get_uom(self.base_uom)
        if self.tracking_mode.requires_serial and (
            self.base_uom != UomCodeVO("PCS") or self.quantity_rules.step != Decimal(1)
        ):
            raise InvalidTrackingConfigurationError(
                "Серийный учёт требует PCS и шаг 1."
            )
