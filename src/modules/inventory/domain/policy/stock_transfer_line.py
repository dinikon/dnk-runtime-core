from decimal import Decimal

from src.modules.inventory.domain.error import QuantityConversionMismatchError
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferLineError,
    StockTransferItemMismatchError,
    StockTransferUomMismatchError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class StockTransferLinePolicy:
    """Сверяет плановую строку перемещения с текущими настройками количества товара."""

    @staticmethod
    def ensure_compatible(
        *,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
        inventory_item: InventoryItemStockSnapshot,
    ) -> None:
        """Требует тот же товар и базовую единицу, актуальный коэффициент пересчёта и кратность текущему шагу."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок товара для строки перемещения."
            )
        inventory_item.ensure_valid()
        if (
            not isinstance(inventory_item_id, InventoryItemIdVO)
            or not isinstance(base_uom, UomCodeVO)
            or not isinstance(planned_qty, QuantityVO)
            or planned_qty.value.is_zero()
            or not isinstance(conversion, QuantityConversionSnapshotVO)
        ):
            raise InvalidStockTransferLineError(
                "Нужны типизированные значения положительной плановой строки."
            )
        if inventory_item_id != inventory_item.inventory_item_id:
            raise StockTransferItemMismatchError(
                "Снимок товара не соответствует строке перемещения."
            )
        if base_uom != inventory_item.base_uom:
            raise StockTransferUomMismatchError(
                "Базовая единица строки не соответствует текущему товару."
            )
        expected = UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(1)),
            from_uom=conversion.uom,
            to_uom=base_uom,
        )
        if (
            conversion.factor_to_base != expected.value
            or conversion.to_base_quantity() != planned_qty
        ):
            raise QuantityConversionMismatchError(
                "Строка перемещения не соответствует текущему системному пересчёту."
            )
        QuantityValidationPolicy.validate(
            quantity=planned_qty, rules=inventory_item.quantity_rules
        )
