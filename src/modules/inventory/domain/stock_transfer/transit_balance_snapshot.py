from dataclasses import dataclass

from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferTransitBalanceError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.transit import (
    StockTransferTransitVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockTransferTransitBalanceLineSnapshot:
    """Передаёт положительный остаток конкретного состава строки в фиксированной локации транзита."""

    transfer_line_id: StockTransferLineIdVO
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO
    quantity: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, положительность и единичность серийного экземпляра."""
        if (
            not isinstance(self.transfer_line_id, StockTransferLineIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Некорректная строка остатка транзита."
            )
        get_uom(self.base_uom)
        if self.dimensions.serial_id is not None and (
            self.base_uom != UomCodeVO("PCS") or self.quantity.value != 1
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Серийный остаток требует 1 PCS."
            )


@dataclass(frozen=True, slots=True)
class StockTransferTransitBalanceSnapshot:
    """Фиксирует вычисленный остаток и использованные ID по полной принятой истории одной версии перемещения."""

    transfer_id: StockTransferIdVO
    transfer_version: int
    source_warehouse_id: WarehouseIdVO
    destination_warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    transit: StockTransferTransitVO
    lines: tuple[StockTransferTransitBalanceLineSnapshot, ...]
    execution_ids: tuple[StockExecutionIdVO, ...]
    execution_line_ids: tuple[StockExecutionLineIdVO, ...]

    def ensure_valid(self) -> None:
        """Проверяет маршрут, строгую версию, состав, уникальность ключей/серий и исторических ID."""
        if (
            not isinstance(self.transfer_id, StockTransferIdVO)
            or type(self.transfer_version) is not int
            or self.transfer_version < 0
            or not isinstance(self.source_warehouse_id, WarehouseIdVO)
            or not isinstance(self.destination_warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.transit, StockTransferTransitVO)
            or self.source_warehouse_id == self.destination_warehouse_id
            or self.transit.warehouse_id
            in (self.source_warehouse_id, self.destination_warehouse_id)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Нужен типизированный остаток транзита с версией и маршрутом."
            )
        for values, expected_type in (
            (self.execution_ids, StockExecutionIdVO),
            (self.execution_line_ids, StockExecutionLineIdVO),
        ):
            if (
                not isinstance(values, tuple)
                or not values
                or not all(isinstance(value, expected_type) for value in values)
                or len(set(values)) != len(values)
            ):
                raise InvalidStockTransferTransitBalanceError(
                    "Исторические ID должны быть типизированными и уникальными."
                )
        keys, serials = set(), set()
        for line in self.lines:
            if not isinstance(line, StockTransferTransitBalanceLineSnapshot):
                raise InvalidStockTransferTransitBalanceError(
                    "Нужны снимки строк транзитного остатка."
                )
            line.ensure_valid()
            key = (line.transfer_line_id, line.dimensions, line.base_uom)
            serial = line.dimensions.serial_id
            if (
                key in keys
                or line.dimensions.owner_id != self.owner_id
                or line.dimensions.location_id != self.transit.location_id
                or (serial is not None and serial in serials)
            ):
                raise InvalidStockTransferTransitBalanceError(
                    "Ключи и серии уникальны; владелец и адрес соответствуют транзиту."
                )
            keys.add(key)
            if serial is not None:
                serials.add(serial)
