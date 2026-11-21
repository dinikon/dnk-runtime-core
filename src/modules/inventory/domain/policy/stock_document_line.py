from decimal import Decimal

from src.modules.inventory.domain.error import QuantityConversionMismatchError
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentLineError,
    StockDocumentItemMismatchError,
    StockDocumentUomMismatchError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class StockDocumentLinePolicy:
    """Проверяет плановое количество и сохранённую единицу по актуальному снимку товара."""

    @staticmethod
    def ensure_compatible(
        *,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
        inventory_item: InventoryItemDocumentSnapshot,
    ) -> None:
        """Требует тот же товар и базовую единицу, положительность, точный пересчёт и кратность шагу."""
        if not isinstance(inventory_item, InventoryItemDocumentSnapshot):
            raise InvalidInventoryItemDocumentSnapshotError(
                "Нужен снимок товара для документа."
            )
        inventory_item.ensure_valid()
        if (
            not isinstance(inventory_item_id, InventoryItemIdVO)
            or not isinstance(base_uom, UomCodeVO)
            or not isinstance(planned_qty, QuantityVO)
            or planned_qty.value.is_zero()
            or not isinstance(conversion, QuantityConversionSnapshotVO)
        ):
            raise InvalidStockDocumentLineError(
                "Нужны типизированные значения с положительным плановым количеством."
            )
        if inventory_item_id != inventory_item.inventory_item_id:
            raise StockDocumentItemMismatchError(
                "Снимок товара не соответствует строке."
            )
        if base_uom != inventory_item.base_uom:
            raise StockDocumentUomMismatchError(
                "Базовая единица товара изменилась; переинтерпретация плана запрещена."
            )
        expected = UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(1)), from_uom=conversion.uom, to_uom=base_uom
        )
        if (
            conversion.factor_to_base != expected.value
            or conversion.to_base_quantity() != planned_qty
        ):
            raise QuantityConversionMismatchError(
                "Плановое количество и коэффициент не соответствуют системному пересчёту."
            )
        QuantityValidationPolicy.validate(
            quantity=planned_qty, rules=inventory_item.quantity_rules
        )
