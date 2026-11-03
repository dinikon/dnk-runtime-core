from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    QuantityConversionMismatchError,
)
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.policy.stock_document_line import (
    StockDocumentLinePolicy,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentLineError,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockDocumentLine:
    """Неизменяемая плановая строка, принадлежащая документу без физических измерений и дельт."""

    id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    sku: SkuVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    conversion: QuantityConversionSnapshotVO
    executed_qty: QuantityVO

    @classmethod
    def create(
        cls,
        *,
        identifier: StockDocumentLineIdVO,
        inventory_item: InventoryItemDocumentSnapshot,
        quantity: QuantityVO,
        uom: UomCodeVO,
    ) -> Self:
        """Создаёт положительный план, вычисляя базовое количество и фиксируя SKU товара."""
        if not isinstance(inventory_item, InventoryItemDocumentSnapshot):
            raise InvalidInventoryItemDocumentSnapshotError(
                "Нужен снимок товара для плановой строки."
            )
        inventory_item.ensure_valid()
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=inventory_item.base_uom
        )
        line = cls.restore(
            identifier=identifier,
            inventory_item_id=inventory_item.inventory_item_id,
            sku=inventory_item.sku,
            base_uom=inventory_item.base_uom,
            planned_qty=conversion.to_base_quantity(),
            conversion=conversion,
            executed_qty=QuantityVO(Decimal(0)),
        )
        line.ensure_compatible(inventory_item)
        return line

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockDocumentLineIdVO,
        inventory_item_id: InventoryItemIdVO,
        sku: SkuVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
        executed_qty: QuantityVO,
    ) -> Self:
        """Восстанавливает собственный исторический состав без текущих правил или смены SKU."""
        line = cls(
            identifier,
            inventory_item_id,
            sku,
            base_uom,
            planned_qty,
            conversion,
            executed_qty,
        )
        line.ensure_valid()
        return line

    def ensure_valid(self) -> None:
        """Проверяет положительный план, исполнение от нуля до плана и точность сохранённого пересчёта."""
        if (
            not isinstance(self.id, StockDocumentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.sku, SkuVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.conversion, QuantityConversionSnapshotVO)
            or not isinstance(self.executed_qty, QuantityVO)
            or self.executed_qty.value > self.planned_qty.value
        ):
            raise InvalidStockDocumentLineError(
                "Строка требует типизированные значения и положительное плановое количество."
            )
        if (
            get_uom(self.base_uom).dimension
            is not get_uom(self.conversion.uom).dimension
        ):
            raise IncompatibleUomError(
                "Исходная и базовая единицы строки должны иметь одну размерность."
            )
        if self.conversion.to_base_quantity() != self.planned_qty:
            raise QuantityConversionMismatchError(
                "Плановое количество не равно сохранённому пересчёту."
            )

    @property
    def remaining_qty(self) -> QuantityVO:
        """Вычисляет точный остаток плана без отдельного сохранённого поля."""
        self.ensure_valid()
        return QuantityArithmeticPolicy.subtract(self.planned_qty, self.executed_qty)

    def ensure_compatible(self, inventory_item: InventoryItemDocumentSnapshot) -> None:
        """Проверяет собственный состав и актуальную совместимость с настройками товара."""
        self.ensure_valid()
        StockDocumentLinePolicy.ensure_compatible(
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            planned_qty=self.planned_qty,
            conversion=self.conversion,
            inventory_item=inventory_item,
        )
