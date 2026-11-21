from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    CountSheetSourceMismatchError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class CountSheetLinePolicy:
    """Проверяет новое или передаваемое фактическое количество по текущим настройкам товара."""

    @staticmethod
    def ensure_compatible(
        *,
        line: CountLine,
        inventory_item: InventoryItemStockSnapshot,
        quantity: QuantityVO,
    ) -> None:
        """Сохраняет идентичность, базовую единицу и LOT/SERIAL, проверяя шаг только факта, а не исторического остатка."""
        if not isinstance(line, CountLine):
            raise InvalidCountLineError("Нужна дочерняя строка ведомости.")
        line.ensure_valid()
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError("Нужен учётный снимок товара.")
        inventory_item.ensure_valid()
        requires_lot = inventory_item.tracking_mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        )
        if (
            inventory_item.inventory_item_id != line.dimensions.inventory_item_id
            or inventory_item.base_uom != line.base_uom
            or requires_lot != (line.dimensions.lot_id is not None)
            or inventory_item.tracking_mode.requires_serial
            != (line.dimensions.serial_id is not None)
        ):
            raise CountSheetSourceMismatchError(
                "Товар, единица и режим LOT/SERIAL должны соответствовать строке."
            )
        QuantityValidationPolicy.validate(
            quantity=quantity, rules=inventory_item.quantity_rules
        )
