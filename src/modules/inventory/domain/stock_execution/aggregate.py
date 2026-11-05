from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.inventory_count.adjustment_source_snapshot import (
    InventoryCountAdjustmentSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.policy.stock_adjustment_execution import (
    StockAdjustmentExecutionPolicy,
)
from src.modules.inventory.domain.policy.stock_adjustment_routes import (
    StockAdjustmentRoutesPolicy,
)
from src.modules.inventory.domain.stock_document.adjustment_execution_snapshot import (
    StockDocumentAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_execution.adjustment_snapshot import (
    StockAdjustmentExecutionSnapshot,
    StockAdjustmentExecutionLineSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.adjustment_line_binding import (
    StockAdjustmentExecutionLineBindingVO,
)
from src.modules.inventory.domain.stock_execution.value_object.adjustment_route import (
    StockAdjustmentExecutionRouteVO,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_execution.transfer_document_snapshot import (
    StockExecutionTransferDocumentSnapshot,
    StockExecutionTransferDocumentLineSnapshot,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferLineSnapshot,
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_execution.shipment_snapshot import (
    StockExecutionShipmentLineSnapshot,
    StockExecutionShipmentSnapshot,
)

from src.modules.inventory.domain.stock_execution.reservation_snapshot import (
    StockExecutionReservationLineSnapshot,
    StockExecutionReservationSnapshot,
)
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
    InvalidStockExecutionTransferSnapshotError,
    InvalidStockExecutionTransferDocumentSnapshotError,
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
    def create_from_inventory_count_adjustment(
        cls,
        *,
        identifier: StockExecutionIdVO,
        document: StockDocumentAdjustmentExecutionSnapshot,
        bindings: tuple[StockAdjustmentExecutionLineBindingVO, ...],
        executed_at: datetime,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> Self:
        """Фиксирует все поправки целиком после проверки зарегистрированного результата, полного основания и SERIAL."""
        normalized = cls._normalize_time(executed_at)
        snapshot = StockAdjustmentExecutionPolicy.build_snapshot(
            identifier=identifier,
            document=document,
            bindings=bindings,
            executed_at=normalized,
        )
        StockAdjustmentExecutionPolicy.ensure_current(
            execution=snapshot,
            document=document,
            inventory_count=inventory_count,
            result=result,
            baseline=baseline,
            warehouse=warehouse,
            inventory_items=inventory_items,
            locations=locations,
            positions=positions,
            as_of=normalized,
            presence=presence,
            lots=lots,
            serials=serials,
        )
        return cls.restore(
            identifier=snapshot.id,
            document_id=snapshot.document_id,
            document_version=snapshot.document_version,
            operation_type=StockOperationType.ADJUSTMENT,
            warehouse_id=snapshot.warehouse_id,
            owner_id=snapshot.owner_id,
            executed_at=snapshot.executed_at,
            lines=tuple(row.as_line() for row in snapshot.lines),
        )

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

    def transfer_document_snapshot(self) -> StockExecutionTransferDocumentSnapshot:
        """Передаёт проверенный физический факт вместе с основанием и версией документа для автоматической регистрации отправки."""
        self._validate()
        if self.operation_type not in (
            StockOperationType.ISSUE,
            StockOperationType.RECEIPT,
        ):
            raise InvalidStockExecutionTransferDocumentSnapshotError(
                "Документный снимок перемещения поддерживает только ISSUE и RECEIPT."
            )
        return StockExecutionTransferDocumentSnapshot(
            self.id,
            self.document_id,
            self.document_version,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockExecutionTransferDocumentLineSnapshot(
                    line.id,
                    line.document_line_id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.quantity,
                    line.route.dimensions[0],
                )
                for line in self.lines
            ),
        )

    def transfer_snapshot(self) -> StockExecutionTransferSnapshot:
        """Передаёт проверенный расход/приход с физическими измерениями без исходного пересчёта и полного маршрута."""
        self._validate()
        if self.operation_type not in (
            StockOperationType.ISSUE,
            StockOperationType.RECEIPT,
        ):
            raise InvalidStockExecutionTransferSnapshotError(
                "Для пары перемещения нужен ISSUE или RECEIPT, а не INTERNAL_MOVE."
            )
        return StockExecutionTransferSnapshot(
            self.id,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockExecutionTransferLineSnapshot(
                    line.id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.quantity,
                    line.route.dimensions[0],
                )
                for line in self.lines
            ),
        )

    def shipment_snapshot(self) -> StockExecutionShipmentSnapshot:
        """Передаёт проверенные фактические строки с ID/версией документа для автоматического назначения Shipment."""
        self._validate()
        self._ensure_ordinary_projection()
        return StockExecutionShipmentSnapshot(
            self.id,
            self.document_id,
            self.document_version,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockExecutionShipmentLineSnapshot(
                    line.id,
                    line.document_line_id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.quantity,
                )
                for line in self.lines
            ),
        )

    def reservation_snapshot(self) -> StockExecutionReservationSnapshot:
        """Возвращает проверенные базовые строки, область и время без передачи Entity погашению резервов."""
        self._validate()
        self._ensure_ordinary_projection()
        return StockExecutionReservationSnapshot(
            self.id,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockExecutionReservationLineSnapshot(
                    line.id, line.inventory_item_id, line.base_uom, line.quantity
                )
                for line in self.lines
            ),
        )

    def posting_snapshot(self) -> StockExecutionPostingSnapshot:
        """Возвращает проверенные физические маршруты и исходные пересчёты без группировки по плану."""
        self._validate()
        self._ensure_ordinary_projection()
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
        self._ensure_ordinary_projection()
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

    def adjustment_snapshot(self) -> StockAdjustmentExecutionSnapshot:
        """Передаёт полный проверенный факт корректировки с целями и позициями для Ledger и документа."""
        self._validate()
        if self.operation_type is not StockOperationType.ADJUSTMENT:
            raise StockAdjustmentError("Нужен факт ADJUSTMENT.")
        snapshot = StockAdjustmentExecutionSnapshot(
            self.id,
            self.document_id,
            self.document_version,
            self.warehouse_id,
            self.owner_id,
            self.executed_at,
            tuple(
                StockAdjustmentExecutionLineSnapshot(
                    line.id, line.document_line_id, line.base_uom, line.route
                )
                for line in self.lines
            ),
        )
        snapshot.ensure_valid()
        return snapshot

    def _ensure_ordinary_projection(self) -> None:
        """Закрывает упрощённые снимки, теряющие знаки корректировки, и погашение резервов этим видом операции."""
        if self.operation_type is StockOperationType.ADJUSTMENT:
            raise StockAdjustmentError(
                "Для ADJUSTMENT нужен adjustment_snapshot; обычные проекции не поддерживаются."
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
            StockOperationType.ADJUSTMENT: StockAdjustmentExecutionRouteVO,
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
            if line.document_line_id in planned_items and (
                self.operation_type is StockOperationType.ADJUSTMENT
                or planned_items[line.document_line_id] != identity
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
            if (
                self.operation_type is not StockOperationType.ADJUSTMENT
                and serials.intersection(line_serials)
            ):
                raise DuplicateStockExecutionSerialError(
                    "Один серийный экземпляр нельзя повторять в разных фактических строках."
                )
            serials.update(line_serials)
        if self.operation_type is StockOperationType.ADJUSTMENT:
            StockAdjustmentRoutesPolicy.ensure_valid(
                tuple(line.route for line in self.lines)
            )

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
