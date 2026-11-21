from datetime import datetime

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
from src.modules.inventory.domain.policy.inventory_count_adjustment_document import (
    InventoryCountAdjustmentDocumentPolicy,
)
from src.modules.inventory.domain.policy.stock_serial_presence import (
    StockSerialPresencePolicy,
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
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class StockAdjustmentExecutionPolicy:
    """Проверяет полный факт относительно подтверждённого плана, зарегистрированного результата и свежего основания."""

    @staticmethod
    def build_snapshot(
        *,
        identifier: StockExecutionIdVO,
        document: StockDocumentAdjustmentExecutionSnapshot,
        bindings: tuple[StockAdjustmentExecutionLineBindingVO, ...],
        executed_at: datetime,
    ) -> StockAdjustmentExecutionSnapshot:
        """Назначает ID каждой полной строке; текущий контекст проверяется отдельно перед созданием факта."""
        if not isinstance(document, StockDocumentAdjustmentExecutionSnapshot):
            raise StockAdjustmentError(
                "Нужен снимок подтверждённого плана корректировки."
            )
        document.ensure_valid()
        if not isinstance(bindings, tuple):
            raise StockAdjustmentError("Нужен tuple назначений ID исполнения.")
        by_id = {}
        for binding in bindings:
            if (
                not isinstance(binding, StockAdjustmentExecutionLineBindingVO)
                or binding.document_line_id in by_id
            ):
                raise StockAdjustmentError(
                    "Нужны уникальные назначения строк документа."
                )
            by_id[binding.document_line_id] = binding
        if set(by_id) != {row.id for row in document.lines}:
            raise StockAdjustmentError("Нужно исполнить ровно все строки плана.")
        rows = []
        for row in document.lines:
            route = StockAdjustmentExecutionRouteVO(
                row.adjustment,
                by_id[row.id].position_id,
                (
                    0
                    if row.adjustment.position_id is None
                    else row.adjustment.position_version
                ),
            )
            rows.append(
                StockAdjustmentExecutionLineSnapshot(
                    by_id[row.id].execution_line_id, row.id, row.base_uom, route
                )
            )
        snapshot = StockAdjustmentExecutionSnapshot(
            identifier,
            document.id,
            document.version,
            document.warehouse_id,
            document.owner_id,
            executed_at,
            tuple(rows),
        )
        StockAdjustmentExecutionPolicy.ensure_document(
            execution=snapshot, document=document
        )
        return snapshot

    @staticmethod
    def ensure_document(
        *,
        execution: StockAdjustmentExecutionSnapshot,
        document: StockDocumentAdjustmentExecutionSnapshot,
    ) -> None:
        """Сверяет всю версию плана, исходные поправки, единицы и время без потери знака или цели."""
        if not isinstance(
            execution, StockAdjustmentExecutionSnapshot
        ) or not isinstance(document, StockDocumentAdjustmentExecutionSnapshot):
            raise StockAdjustmentError(
                "Нужны специализированные снимки плана и факта корректировки."
            )
        execution.ensure_valid()
        document.ensure_valid()
        if (
            execution.document_id != document.id
            or execution.document_version != document.version
            or execution.warehouse_id != document.warehouse_id
            or execution.owner_id != document.owner_id
            or execution.executed_at < document.updated_at
        ):
            raise StockAdjustmentError(
                "Факт не соответствует текущей версии, области или времени плана."
            )
        planned = {line.id: line for line in document.lines}
        if set(planned) != {line.document_line_id for line in execution.lines}:
            raise StockAdjustmentError(
                "Корректировка исполняет все строки целиком один раз."
            )
        for row in execution.lines:
            line = planned[row.document_line_id]
            if row.base_uom != line.base_uom or row.route.adjustment != line.adjustment:
                raise StockAdjustmentError(
                    "Знак, цель, измерения или исходная позиция факта подменены."
                )

    @staticmethod
    def ensure_current(
        *,
        execution: StockAdjustmentExecutionSnapshot,
        document: StockDocumentAdjustmentExecutionSnapshot,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        as_of: datetime,
        presence: tuple[StockSerialPresenceSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> None:
        """Повторно проверяет весь исходный запас до подготовки новых позиций и до проведения."""
        StockAdjustmentExecutionPolicy.ensure_document(
            execution=execution, document=document
        )
        InventoryCountAdjustmentDocumentPolicy.ensure_confirmable(
            source=document.source,
            warehouse_id=document.warehouse_id,
            owner_id=document.owner_id,
            lines=tuple(row.as_line() for row in document.lines),
            inventory_count=inventory_count,
            result=result,
            baseline=baseline,
            warehouse=warehouse,
            inventory_items=inventory_items,
            locations=locations,
            positions=positions,
            as_of=as_of,
            lots=lots,
            serials=serials,
        )
        if as_of < execution.executed_at:
            raise StockAdjustmentError("Проведение не может предшествовать исполнению.")
        known = {position.id for position in positions}
        for row in execution.lines:
            if (
                row.route.adjustment.position_id is None
                and row.route.position_id in known
            ):
                raise StockAdjustmentError(
                    "FOUND требует новый ID позиции, отсутствующий во всём основании."
                )
        StockSerialPresencePolicy.ensure_compatible(
            routes=tuple(row.route for row in execution.lines), presence=presence
        )
