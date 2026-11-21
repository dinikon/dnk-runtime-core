from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferDocumentSnapshotError,
    InvalidStockExecutionTransferSnapshotError,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferLineSnapshot,
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockExecutionTransferDocumentLineSnapshot:
    """Передаёт целую фактическую строку, её документную связь и сохраняемые физические измерения."""

    execution_line_id: StockExecutionLineIdVO
    document_line_id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    dimensions: StockDimensionsVO

    def ensure_valid(self) -> None:
        """Проверяет тип документной связи и прежние правила положительного количества и серийного экземпляра."""
        if not isinstance(self.document_line_id, StockDocumentLineIdVO):
            raise InvalidStockExecutionTransferDocumentSnapshotError(
                "Нужен типизированный ID строки документа факта."
            )
        try:
            StockExecutionTransferLineSnapshot(
                self.execution_line_id,
                self.inventory_item_id,
                self.base_uom,
                self.quantity,
                self.dimensions,
            ).ensure_valid()
        except InvalidStockExecutionTransferSnapshotError as exc:
            raise InvalidStockExecutionTransferDocumentSnapshotError(
                "Некорректная фактическая строка с документным основанием."
            ) from exc


@dataclass(frozen=True, slots=True)
class StockExecutionTransferDocumentSnapshot:
    """Связывает расход или приход с версией документа, не теряя LOT/SERIAL и состояние."""

    id: StockExecutionIdVO
    document_id: StockDocumentIdVO
    document_version: int
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockExecutionTransferDocumentLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет строгую документную версию и все прежние физические инварианты без запрета нескольких фактов одной строки плана."""
        if (
            not isinstance(self.document_id, StockDocumentIdVO)
            or type(self.document_version) is not int
            or self.document_version < 0
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockExecutionTransferDocumentSnapshotError(
                "Нужны типизированное основание, строгая версия и tuple фактических строк."
            )
        for line in self.lines:
            if not isinstance(line, StockExecutionTransferDocumentLineSnapshot):
                raise InvalidStockExecutionTransferDocumentSnapshotError(
                    "Нужны снимки фактических строк с документными связями."
                )
            line.ensure_valid()
        try:
            self._physical_snapshot().ensure_valid()
        except InvalidStockExecutionTransferSnapshotError as exc:
            raise InvalidStockExecutionTransferDocumentSnapshotError(
                "Некорректный ISSUE/RECEIPT: проверьте UTC, владельца, фактические ID и серии."
            ) from exc

    def transfer_snapshot(self) -> StockExecutionTransferSnapshot:
        """После проверки возвращает прежний физический контракт для согласования отправки."""
        self.ensure_valid()
        return self._physical_snapshot()

    def _physical_snapshot(self) -> StockExecutionTransferSnapshot:
        """Проецирует собственные проверяемые поля в прежний контракт без обращения к другому корню."""
        return StockExecutionTransferSnapshot(
            self.id,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockExecutionTransferLineSnapshot(
                    line.execution_line_id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.quantity,
                    line.dimensions,
                )
                for line in self.lines
            ),
        )
