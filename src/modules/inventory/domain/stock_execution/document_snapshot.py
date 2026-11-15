from src.modules.inventory.domain.stock_document.value_object.return_details import (
    StockReturnDetailsVO,
)
from src.modules.inventory.domain.policy.return_details import ReturnDetailsPolicy
from src.modules.inventory.domain.stock_document.value_object.status_change_details import (
    StockStatusChangeDetailsVO,
)
from src.modules.inventory.domain.policy.status_change_details import (
    StatusChangeDetailsPolicy,
)
from src.modules.inventory.domain.stock_document.value_object.write_off_reason import (
    WriteOffReasonVO,
)
from src.modules.inventory.domain.policy.write_off_reason import WriteOffReasonPolicy
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionDocumentSnapshotError,
)
from src.modules.inventory.domain.stock_execution.value_object.document_line_quantity import (
    ExecutedDocumentLineQuantityVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockExecutionDocumentSnapshot:
    """Передаёт только основание, версию и положительные итоги плановых строк без маршрутов."""

    id: StockExecutionIdVO
    document_id: StockDocumentIdVO
    document_version: int
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[ExecutedDocumentLineQuantityVO, ...]

    write_off_reason: WriteOffReasonVO | None = None
    status_change_details: StockStatusChangeDetailsVO | None = None
    return_details: StockReturnDetailsVO | None = None

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, UTC-время и уникальные непустые итоги строк."""
        ReturnDetailsPolicy.ensure_compatible(self.operation_type, self.return_details)
        StatusChangeDetailsPolicy.ensure_compatible(
            self.operation_type, self.status_change_details
        )
        WriteOffReasonPolicy.ensure_compatible(
            self.operation_type, self.write_off_reason
        )
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.document_id, StockDocumentIdVO)
            or type(self.document_version) is not int
            or self.document_version < 0
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockExecutionDocumentSnapshotError(
                "Нужен типизированный непустой снимок исполнения с версией и UTC-временем."
            )
        ids = set()
        for line in self.lines:
            if (
                not isinstance(line, ExecutedDocumentLineQuantityVO)
                or line.document_line_id in ids
            ):
                raise InvalidStockExecutionDocumentSnapshotError(
                    "Итоги плановых строк должны быть типизированы и уникальны."
                )
            ids.add(line.document_line_id)
