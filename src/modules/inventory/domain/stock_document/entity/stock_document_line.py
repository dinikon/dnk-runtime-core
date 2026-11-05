from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.policy.stock_adjustment_line import (
    StockAdjustmentLinePolicy,
)
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)

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
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockDocumentLine:
    """Неизменяемая плановая строка с отдельным физическим основанием только для корректировки."""

    id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    sku: SkuVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    conversion: QuantityConversionSnapshotVO
    executed_qty: QuantityVO
    source: DocumentLineSourceVO | None
    adjustment: StockAdjustmentLineVO | None

    @classmethod
    def create_adjustment(
        cls,
        *,
        identifier: StockDocumentLineIdVO,
        inventory_item: InventoryItemDocumentSnapshot,
        adjustment: StockAdjustmentLineVO,
        source: DocumentLineSourceVO,
    ) -> Self:
        """Фиксирует модуль точной дельты в базовой единице, проверяя шаг только целевого остатка."""
        if not isinstance(
            inventory_item, InventoryItemDocumentSnapshot
        ) or not isinstance(adjustment, StockAdjustmentLineVO):
            raise InvalidStockDocumentLineError(
                "Нужны снимок товара и основание корректировки."
            )
        inventory_item.ensure_valid()
        quantity = QuantityVO(adjustment.quantity_delta.value.copy_abs())
        line = cls.restore(
            identifier=identifier,
            inventory_item_id=inventory_item.inventory_item_id,
            sku=inventory_item.sku,
            base_uom=inventory_item.base_uom,
            planned_qty=quantity,
            conversion=QuantityConversionSnapshotVO(
                quantity, inventory_item.base_uom, Decimal(1)
            ),
            executed_qty=QuantityVO(Decimal(0)),
            source=source,
            adjustment=adjustment,
        )
        line.ensure_compatible(inventory_item)
        return line

    @classmethod
    def create(
        cls,
        *,
        identifier: StockDocumentLineIdVO,
        inventory_item: InventoryItemDocumentSnapshot,
        quantity: QuantityVO,
        uom: UomCodeVO,
        source: DocumentLineSourceVO | None = None,
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
            source=source,
            adjustment=None,
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
        source: DocumentLineSourceVO | None,
        adjustment: StockAdjustmentLineVO | None,
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
            source,
            adjustment,
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
            or (
                self.source is not None
                and not isinstance(self.source, DocumentLineSourceVO)
            )
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
        if self.adjustment is not None:
            if (
                not isinstance(self.adjustment, StockAdjustmentLineVO)
                or self.inventory_item_id
                != self.adjustment.dimensions.inventory_item_id
                or self.planned_qty.value
                != self.adjustment.quantity_delta.value.copy_abs()
                or self.conversion.uom != self.base_uom
                or self.conversion.factor_to_base != Decimal(1)
                or self.executed_qty.value not in (Decimal(0), self.planned_qty.value)
                or (
                    self.adjustment.dimensions.serial_id is not None
                    and self.base_uom != UomCodeVO("PCS")
                )
            ):
                raise InvalidStockDocumentLineError(
                    "Корректировка требует точную дельту в базовой единице, нулевое или полное исполнение и PCS для SERIAL."
                )

    @property
    def remaining_qty(self) -> QuantityVO:
        """Вычисляет точный остаток плана без отдельного сохранённого поля."""
        self.ensure_valid()
        return QuantityArithmeticPolicy.subtract(self.planned_qty, self.executed_qty)

    def ensure_compatible(self, inventory_item: InventoryItemDocumentSnapshot) -> None:
        """Проверяет собственный состав и актуальную совместимость с настройками товара."""
        self.ensure_valid()
        if self.adjustment is not None:
            StockAdjustmentLinePolicy.ensure_compatible(
                inventory_item_id=self.inventory_item_id,
                base_uom=self.base_uom,
                adjustment=self.adjustment,
                inventory_item=inventory_item,
            )
            return
        StockDocumentLinePolicy.ensure_compatible(
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            planned_qty=self.planned_qty,
            conversion=self.conversion,
            inventory_item=inventory_item,
        )
