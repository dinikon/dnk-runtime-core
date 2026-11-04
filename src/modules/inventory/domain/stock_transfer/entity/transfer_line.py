from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    QuantityConversionMismatchError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_transfer_line import (
    StockTransferLinePolicy,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferLineError,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class TransferLine:
    """План количества товара без адресов, конкретных партий/серий и прогресса исполнения."""

    id: StockTransferLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    conversion: QuantityConversionSnapshotVO

    @classmethod
    def create(
        cls,
        *,
        identifier: StockTransferLineIdVO,
        inventory_item: InventoryItemStockSnapshot,
        quantity: QuantityVO,
        uom: UomCodeVO,
    ) -> Self:
        """Фиксирует исходный ввод и вычисляет базовый положительный план по текущим настройкам товара."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок товара строки перемещения."
            )
        inventory_item.ensure_valid()
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=inventory_item.base_uom
        )
        line = cls.restore(
            identifier=identifier,
            inventory_item_id=inventory_item.inventory_item_id,
            base_uom=inventory_item.base_uom,
            planned_qty=conversion.to_base_quantity(),
            conversion=conversion,
        )
        line.ensure_compatible(inventory_item=inventory_item)
        return line

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockTransferLineIdVO,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
    ) -> Self:
        """Восстанавливает полный собственный исторический состав без текущих товарных правил."""
        line = cls(identifier, inventory_item_id, base_uom, planned_qty, conversion)
        line.ensure_valid()
        return line

    def ensure_valid(self) -> None:
        """Проверяет типы, положительный план, одну размерность и равенство сохранённому пересчёту."""
        if (
            not isinstance(self.id, StockTransferLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.conversion, QuantityConversionSnapshotVO)
        ):
            raise InvalidStockTransferLineError(
                "Нужна типизированная строка с положительным плановым количеством."
            )
        if (
            get_uom(self.base_uom).dimension
            is not get_uom(self.conversion.uom).dimension
        ):
            raise IncompatibleUomError(
                "Исходная и базовая единицы перемещения должны иметь одну размерность."
            )
        if self.conversion.to_base_quantity() != self.planned_qty:
            raise QuantityConversionMismatchError(
                "План строки перемещения не равен сохранённому пересчёту."
            )

    def ensure_compatible(self, *, inventory_item: InventoryItemStockSnapshot) -> None:
        """Повторно проверяет собственный состав и совместимость с актуальным учётным снимком товара."""
        self.ensure_valid()
        StockTransferLinePolicy.ensure_compatible(
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            planned_qty=self.planned_qty,
            conversion=self.conversion,
            inventory_item=inventory_item,
        )
