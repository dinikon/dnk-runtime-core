from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferDispatchDocumentSnapshotError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
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
class StockTransferDispatchDocumentLineSnapshot:
    """Передаёт положительный остаток одной строки перемещения к отправке в базовой единице."""

    transfer_line_id: StockTransferLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    remaining_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет типы, известную единицу и строго положительный остаток."""
        if (
            not isinstance(self.transfer_line_id, StockTransferLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.remaining_qty, QuantityVO)
            or self.remaining_qty.value.is_zero()
        ):
            raise InvalidStockTransferDispatchDocumentSnapshotError(
                "Некорректная строка остатка к отправке."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class StockTransferDispatchDocumentSnapshot:
    """Передаёт направление, версию и только открытые остатки для документов отправки без истории фактов."""

    id: StockTransferIdVO
    version: int
    status: StockTransferStatus
    source_warehouse_id: WarehouseIdVO
    destination_warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    transit: StockTransferTransitVO | None
    updated_at: datetime
    lines: tuple[StockTransferDispatchDocumentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет типы, UTC, версию, направление, уникальность строк и локальные признаки жизненного цикла."""
        if (
            not isinstance(self.id, StockTransferIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, StockTransferStatus)
            or not isinstance(self.source_warehouse_id, WarehouseIdVO)
            or not isinstance(self.destination_warehouse_id, WarehouseIdVO)
            or self.source_warehouse_id == self.destination_warehouse_id
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or (
                self.transit is not None
                and not isinstance(self.transit, StockTransferTransitVO)
            )
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockTransferDispatchDocumentSnapshotError(
                "Нужен типизированный снимок остатка с UTC и строгой версией."
            )
        if self.transit is not None and self.transit.warehouse_id in (
            self.source_warehouse_id,
            self.destination_warehouse_id,
        ):
            raise InvalidStockTransferDispatchDocumentSnapshotError(
                "Транзит должен отличаться от обоих конечных складов."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, StockTransferDispatchDocumentLineSnapshot):
                raise InvalidStockTransferDispatchDocumentSnapshotError(
                    "Нужны снимки открытых строк перемещения."
                )
            line.ensure_valid()
            if line.transfer_line_id in ids:
                raise InvalidStockTransferDispatchDocumentSnapshotError(
                    "Строки основания не должны повторяться."
                )
            ids.add(line.transfer_line_id)
        progressing = self.status in (
            StockTransferStatus.IN_PROGRESS,
            StockTransferStatus.COMPLETED,
        )
        if (
            (progressing and self.transit is None)
            or (not progressing and self.transit is not None)
            or (self.status is StockTransferStatus.CONFIRMED and not self.lines)
            or (self.status is StockTransferStatus.COMPLETED and self.lines)
        ):
            raise InvalidStockTransferDispatchDocumentSnapshotError(
                "Состав остатка или транзит не соответствует статусу перемещения."
            )
