from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_document_progress import (
    StockDocumentProgressPolicy,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentTransferDispatchSnapshotError,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockDocumentTransferDispatchLineSnapshot:
    """Передаёт происхождение и собственный лимит одной строки документа отправки в транзит."""

    document_line_id: StockDocumentLineIdVO
    transfer_line_id: StockTransferLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    executed_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Требует типизированные связи и исполнение в пределах положительного плана."""
        if (
            not isinstance(self.document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.transfer_line_id, StockTransferLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.executed_qty, QuantityVO)
            or self.executed_qty.value > self.planned_qty.value
        ):
            raise InvalidStockDocumentTransferDispatchSnapshotError(
                "Нужна типизированная строка документа с исполнением от нуля до положительного плана."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class StockDocumentTransferDispatchSnapshot:
    """Сохраняет текущую версию документа и историческую версию его основания StockTransfer раздельно."""

    id: StockDocumentIdVO
    version: int
    status: StockDocumentStatus
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    updated_at: datetime
    transfer_id: StockTransferIdVO
    source_transfer_version: int
    lines: tuple[StockDocumentTransferDispatchLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет ISSUE/RECEIPT, UTC, строгие версии, уникальность связей и собственный прогресс документа."""
        if (
            not isinstance(self.id, StockDocumentIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, StockDocumentStatus)
            or not isinstance(self.operation_type, StockOperationType)
            or self.operation_type
            not in (StockOperationType.ISSUE, StockOperationType.RECEIPT)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.transfer_id, StockTransferIdVO)
            or type(self.source_transfer_version) is not int
            or self.source_transfer_version < 0
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockDocumentTransferDispatchSnapshotError(
                "Нужен типизированный снимок ISSUE/RECEIPT с UTC-временем и строгими версиями документа и основания."
            )
        document_ids, transfer_ids = set(), set()
        for line in self.lines:
            if not isinstance(line, StockDocumentTransferDispatchLineSnapshot):
                raise InvalidStockDocumentTransferDispatchSnapshotError(
                    "Нужны снимки строк документа отправки перемещения."
                )
            line.ensure_valid()
            if (
                line.document_line_id in document_ids
                or line.transfer_line_id in transfer_ids
            ):
                raise InvalidStockDocumentTransferDispatchSnapshotError(
                    "ID строк документа и ссылки TransferLine не должны повторяться."
                )
            document_ids.add(line.document_line_id)
            transfer_ids.add(line.transfer_line_id)
        StockDocumentProgressPolicy.ensure_valid(
            status=self.status,
            quantities=tuple(
                (line.planned_qty, line.executed_qty) for line in self.lines
            ),
        )
