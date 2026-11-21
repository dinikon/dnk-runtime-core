from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferDispatchSnapshotError,
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
class StockTransferDispatchedLineSnapshot:
    """Сохраняет количество строки и участвующие целые фактические строки обеих сторон отправки."""

    transfer_line_id: StockTransferLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    issue_execution_line_ids: tuple[StockExecutionLineIdVO, ...]
    receipt_execution_line_ids: tuple[StockExecutionLineIdVO, ...]

    def ensure_valid(self) -> None:
        """Требует положительное количество и непустые уникальные фактические ID каждой стороны."""
        if (
            not isinstance(self.transfer_line_id, StockTransferLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
        ):
            raise InvalidStockTransferDispatchSnapshotError(
                "Некорректная строка результата отправки."
            )
        get_uom(self.base_uom)
        ids = set()
        for values in (self.issue_execution_line_ids, self.receipt_execution_line_ids):
            if (
                not isinstance(values, tuple)
                or not values
                or not all(
                    isinstance(value, StockExecutionLineIdVO) for value in values
                )
            ):
                raise InvalidStockTransferDispatchSnapshotError(
                    "Нужны непустые tuple фактических ID обеих сторон."
                )
            for value in values:
                if value in ids:
                    raise InvalidStockTransferDispatchSnapshotError(
                        "Фактические ID обеих сторон должны быть уникальны."
                    )
                ids.add(value)


@dataclass(frozen=True, slots=True)
class StockTransferDispatchSnapshot:
    """Передаёт согласованный факт пары ISSUE/RECEIPT для одной версии перемещения без истории всех отправок."""

    transfer_id: StockTransferIdVO
    transfer_version: int
    source_warehouse_id: WarehouseIdVO
    destination_warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    transit: StockTransferTransitVO
    issue_execution_id: StockExecutionIdVO
    receipt_execution_id: StockExecutionIdVO
    executed_at: datetime
    lines: tuple[StockTransferDispatchedLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет типы, строгую версию, разные склады/исполнения, UTC и уникальность строк пары."""
        if (
            not isinstance(self.transfer_id, StockTransferIdVO)
            or type(self.transfer_version) is not int
            or self.transfer_version < 0
            or not isinstance(self.source_warehouse_id, WarehouseIdVO)
            or not isinstance(self.destination_warehouse_id, WarehouseIdVO)
            or self.source_warehouse_id == self.destination_warehouse_id
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.transit, StockTransferTransitVO)
            or not isinstance(self.issue_execution_id, StockExecutionIdVO)
            or not isinstance(self.receipt_execution_id, StockExecutionIdVO)
            or self.issue_execution_id == self.receipt_execution_id
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockTransferDispatchSnapshotError(
                "Нужен непустой типизированный результат отправки с UTC-временем и строгой версией."
            )
        if self.transit.warehouse_id in (
            self.source_warehouse_id,
            self.destination_warehouse_id,
        ):
            raise InvalidStockTransferDispatchSnapshotError(
                "Транзитный склад должен отличаться от обоих конечных."
            )
        ids, facts = set(), set()
        for line in self.lines:
            if not isinstance(line, StockTransferDispatchedLineSnapshot):
                raise InvalidStockTransferDispatchSnapshotError(
                    "Нужны снимки отправленных строк."
                )
            line.ensure_valid()
            values = (*line.issue_execution_line_ids, *line.receipt_execution_line_ids)
            if line.transfer_line_id in ids or facts.intersection(values):
                raise InvalidStockTransferDispatchSnapshotError(
                    "Плановые и фактические строки отправки не должны повторяться."
                )
            ids.add(line.transfer_line_id)
            facts.update(values)
