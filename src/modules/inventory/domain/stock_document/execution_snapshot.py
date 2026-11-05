from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_document_progress import (
    StockDocumentProgressPolicy,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentExecutionSnapshotError,
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
class StockDocumentLineExecutionSnapshot:
    """Передаёт лимит одной конкретной плановой строки без её SKU и исходного пересчёта."""

    id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    executed_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы и допустимый диапазон накопленного исполнения."""
        if (
            not isinstance(self.id, StockDocumentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.executed_qty, QuantityVO)
            or self.executed_qty.value > self.planned_qty.value
        ):
            raise InvalidStockDocumentExecutionSnapshotError(
                "Нужен типизированный лимит строки с исполнением от нуля до плана."
            )
        get_uom(self.base_uom)

    @property
    def remaining_qty(self) -> QuantityVO:
        """Вычисляет точный остаток плана без отдельного хранимого поля."""
        self.ensure_valid()
        return QuantityArithmeticPolicy.subtract(self.planned_qty, self.executed_qty)


@dataclass(frozen=True, slots=True)
class StockDocumentExecutionSnapshot:
    """Фиксирует версию, реквизиты и остатки плана для подготовки очередного исполнения."""

    id: StockDocumentIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: StockDocumentStatus
    version: int
    updated_at: datetime
    lines: tuple[StockDocumentLineExecutionSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, уникальность строк, UTC-время и согласованный прогресс."""
        if (
            not isinstance(self.id, StockDocumentIdVO)
            or not isinstance(self.operation_type, StockOperationType)
            or self.operation_type is StockOperationType.ADJUSTMENT
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.status, StockDocumentStatus)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockDocumentExecutionSnapshotError(
                "Нужен типизированный снимок плана с версией и временем UTC."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, StockDocumentLineExecutionSnapshot):
                raise InvalidStockDocumentExecutionSnapshotError(
                    "Нужны снимки плановых строк."
                )
            line.ensure_valid()
            if line.id in ids:
                raise InvalidStockDocumentExecutionSnapshotError(
                    "ID строк плана не должны повторяться."
                )
            ids.add(line.id)
        StockDocumentProgressPolicy.ensure_valid(
            status=self.status,
            quantities=tuple(
                (line.planned_qty, line.executed_qty) for line in self.lines
            ),
        )
