from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockAdjustmentLineError,
)
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class StockAdjustmentLinePolicy:
    """Применяет текущий шаг только к целевому остатку, сохраняя историческое количество без округления."""

    @staticmethod
    def ensure_compatible(
        *,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        adjustment: StockAdjustmentLineVO,
        inventory_item: InventoryItemDocumentSnapshot,
    ) -> None:
        """Требует неизменную идентичность/единицу и допустимый текущими правилами целевой остаток."""
        if not isinstance(inventory_item, InventoryItemDocumentSnapshot):
            raise InvalidStockAdjustmentLineError(
                "Нужен актуальный снимок товара корректировки."
            )
        inventory_item.ensure_valid()
        if (
            not isinstance(adjustment, StockAdjustmentLineVO)
            or inventory_item_id != inventory_item.inventory_item_id
            or inventory_item_id != adjustment.dimensions.inventory_item_id
            or base_uom != inventory_item.base_uom
        ):
            raise InvalidStockAdjustmentLineError(
                "Товар, измерения и базовая единица корректировки должны совпадать."
            )
        QuantityValidationPolicy.validate(
            quantity=adjustment.target_qty, rules=inventory_item.quantity_rules
        )
