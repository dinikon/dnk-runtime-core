from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self

from src.modules.inventory.domain.inventory_item.execution_snapshot import (
    InventoryItemExecutionSnapshot,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_context import (
    StockExecutionContextPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_document import (
    StockExecutionDocumentPolicy,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentExecutionSnapshotError,
)
from src.modules.inventory.domain.stock_document.execution_snapshot import (
    StockDocumentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_execution.document_snapshot import (
    StockExecutionDocumentSnapshot,
)
from src.modules.inventory.domain.stock_execution.posting_snapshot import (
    StockExecutionPostingSnapshot,
    StockExecutionPostingLineSnapshot,
)
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    DuplicateStockExecutionLineError,
    DuplicateStockExecutionSerialError,
    InvalidStockExecutionContextError,
    InvalidStockExecutionRouteError,
    InvalidStockExecutionValueError,
    StockExecutionTimeError,
)
from src.modules.inventory.domain.stock_execution.value_object.document_line_quantity import (
    ExecutedDocumentLineQuantityVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.execution_snapshot import (
    StockSerialExecutionSnapshot,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockExecution:
    """Неизменяемый фактический состав исполнения по версии плана без проведения и изменения остатков."""

    id: StockExecutionIdVO
    document_id: StockDocumentIdVO
    document_version: int
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockExecutionLine, ...]

    @classmethod
    def create(
        cls,
        *,
        identifier: StockExecutionIdVO,
        document: StockDocumentExecutionSnapshot,
        executed_at: datetime,
        lines: tuple[StockExecutionLine, ...],
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemExecutionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialExecutionSnapshot, ...] = (),
    ) -> Self:
        """Фиксирует исполнение после проверки текущего плана, активных адресов, количества и прослеживаемости."""
        if not isinstance(document, StockDocumentExecutionSnapshot):
            raise InvalidStockDocumentExecutionSnapshotError(
                "Нужен снимок плана для создания исполнения."
            )
        document.ensure_valid()
        execution = cls.restore(
            identifier=identifier,
            document_id=document.id,
            document_version=document.version,
            operation_type=document.operation_type,
            warehouse_id=document.warehouse_id,
            owner_id=document.owner_id,
            executed_at=executed_at,
            lines=lines,
        )
        StockExecutionDocumentPolicy.ensure_compatible(
            document=document, execution=execution.snapshot_for_document()
        )
        StockExecutionContextPolicy.ensure_compatible(
            operation_type=execution.operation_type,
            warehouse_id=execution.warehouse_id,
            lines=execution.lines,
            warehouse=warehouse,
            inventory_items=inventory_items,
            locations=locations,
            lots=lots,
            serials=serials,
        )
        return execution

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockExecutionIdVO,
        document_id: StockDocumentIdVO,
        document_version: int,
        operation_type: StockOperationType,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        executed_at: datetime,
        lines: tuple[StockExecutionLine, ...],
    ) -> Self:
        """Восстанавливает полное собственное состояние без актуального плана и снимков физического контекста."""
        execution = cls(
            identifier,
            document_id,
            document_version,
            operation_type,
            warehouse_id,
            owner_id,
            cls._normalize_time(executed_at),
            lines,
        )
        execution._validate()
        return execution

    def posting_snapshot(self) -> StockExecutionPostingSnapshot:
        """Возвращает проверенные физические маршруты и исходные пересчёты без группировки по плану."""
        self._validate()
        return StockExecutionPostingSnapshot(
            self.id,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockExecutionPostingLineSnapshot(
                    line.id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.quantity,
                    line.conversion,
                    line.route,
                )
                for line in self.lines
            ),
        )

    def snapshot_for_document(self) -> StockExecutionDocumentSnapshot:
        """Суммирует положительные количества по плановым строкам, считая перемещение один раз."""
        self._validate()
        grouped = {}
        for line in self.lines:
            previous = grouped.get(line.document_line_id)
            quantity = (
                line.quantity
                if previous is None
                else QuantityArithmeticPolicy.add(previous.quantity, line.quantity)
            )
            grouped[line.document_line_id] = ExecutedDocumentLineQuantityVO(
                line.document_line_id, line.inventory_item_id, line.base_uom, quantity
            )
        return StockExecutionDocumentSnapshot(
            self.id,
            self.document_id,
            self.document_version,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(grouped.values()),
        )

    def _validate(self) -> None:
        """Проверяет собственный состав, вид маршрута, владельца и уникальность фактических экземпляров."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.document_id, StockDocumentIdVO)
            or type(self.document_version) is not int
            or self.document_version < 0
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockExecutionValueError(
                "Нужны типизированные реквизиты, версия плана и непустой tuple фактических строк."
            )
        self._normalize_time(self.executed_at)
        if self.executed_at.utcoffset() != timedelta(0):
            raise StockExecutionTimeError(
                "Сохранённое время исполнения должно быть в UTC."
            )
        route_type = {
            StockOperationType.RECEIPT: ReceiptExecutionRouteVO,
            StockOperationType.ISSUE: IssueExecutionRouteVO,
            StockOperationType.INTERNAL_MOVE: InternalMoveExecutionRouteVO,
        }.get(self.operation_type)
        ids, serials = set(), set()
        planned_items = {}
        for line in self.lines:
            if not isinstance(line, StockExecutionLine):
                raise InvalidStockExecutionValueError(
                    "Нужны фактические StockExecutionLine."
                )
            line.ensure_valid()
            if line.id in ids:
                raise DuplicateStockExecutionLineError(
                    "ID фактических строк должны быть уникальны."
                )
            ids.add(line.id)
            if route_type is None or not isinstance(line.route, route_type):
                raise InvalidStockExecutionRouteError(
                    "Маршрут не соответствует виду операции."
                )
            identity = (line.inventory_item_id, line.base_uom)
            if (
                line.document_line_id in planned_items
                and planned_items[line.document_line_id] != identity
            ):
                raise InvalidStockExecutionContextError(
                    "Одна плановая строка не может исполняться разными товарами или базовыми единицами."
                )
            planned_items[line.document_line_id] = identity
            line_serials = set()
            for dimensions in line.route.dimensions:
                if dimensions.owner_id != self.owner_id:
                    raise InvalidStockExecutionContextError(
                        "Владелец маршрута должен соответствовать документу."
                    )
                if dimensions.serial_id is not None:
                    line_serials.add(dimensions.serial_id)
            if serials.intersection(line_serials):
                raise DuplicateStockExecutionSerialError(
                    "Один серийный экземпляр нельзя повторять в разных фактических строках."
                )
            serials.update(line_serials)

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Требует явное aware datetime и нормализует время в UTC без обращения к часам."""
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise StockExecutionTimeError(
                "Время исполнения должно содержать часовой пояс."
            )
        try:
            return value.astimezone(UTC)
        except (ValueError, OverflowError) as exc:
            raise StockExecutionTimeError(
                "Время исполнения невозможно представить в UTC."
            ) from exc
