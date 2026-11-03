from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class InventoryItemDocumentSnapshot:
    """Передаёт идентичность, SKU и настройки количества для планирования без коллекций товара."""

    inventory_item_id: InventoryItemIdVO
    sku: SkuVO
    base_uom: UomCodeVO
    quantity_rules: QuantityRulesVO
    tracking_mode: TrackingMode

    def ensure_valid(self) -> None:
        """Проверяет типы и существующие инварианты единицы и серийного режима."""
        if (
            not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.sku, SkuVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity_rules, QuantityRulesVO)
            or not isinstance(self.tracking_mode, TrackingMode)
        ):
            raise InvalidInventoryItemDocumentSnapshotError(
                "Нужен типизированный снимок товара для документа."
            )
        InventoryItemStockSnapshot(
            self.inventory_item_id,
            self.base_uom,
            self.quantity_rules,
            self.tracking_mode,
        ).ensure_valid()
