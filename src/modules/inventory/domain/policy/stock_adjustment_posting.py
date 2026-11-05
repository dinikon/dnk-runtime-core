from decimal import Decimal

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_execution.adjustment_snapshot import (
    StockAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_posting.adjustment_entry_snapshot import (
    StockAdjustmentEntrySnapshot,
)
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)


class StockAdjustmentPostingPolicy:
    """Строит несальдированные записи корректировки и связывает их с фактами для применения к позициям."""

    @staticmethod
    def build_entries(
        *,
        execution: StockAdjustmentExecutionSnapshot,
        positions: tuple[StockPositionCountingSnapshot, ...],
        found_positions: tuple[StockPositionCountingSnapshot, ...],
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
    ) -> tuple[StockLedgerEntry, ...]:
        """Требует исходные версии/количества и ровно новые нулевые позиции FOUND, не изменяя основание."""
        if not isinstance(execution, StockAdjustmentExecutionSnapshot):
            raise StockAdjustmentError("Нужен полный факт корректировки.")
        execution.ensure_valid()
        if not all(
            isinstance(values, tuple)
            for values in (positions, found_positions, entry_bindings)
        ):
            raise StockAdjustmentError(
                "Позиции и назначения Ledger передаются в tuple."
            )
        by_position, dimensions = {}, set()
        for position in (*positions, *found_positions):
            if not isinstance(position, StockPositionCountingSnapshot):
                raise StockAdjustmentError(
                    "Нужны снимки количества и версии физического запаса."
                )
            position.ensure_valid()
            if position.id in by_position or position.dimensions in dimensions:
                raise StockAdjustmentError(
                    "Позиции и физические измерения повторяются."
                )
            by_position[position.id] = position
            dimensions.add(position.dimensions)
        expected_found = {
            row.route.position_id
            for row in execution.lines
            if row.route.adjustment.position_id is None
        }
        if {position.id for position in found_positions} != expected_found:
            raise StockAdjustmentError(
                "Нужны ровно новые позиции FOUND, отдельно от исходного основания."
            )
        bindings, identifiers = {}, set()
        for binding in entry_bindings:
            if (
                not isinstance(binding, StockPostingEntryBindingVO)
                or binding.position_id in bindings
                or binding.entry_id in identifiers
            ):
                raise StockAdjustmentError(
                    "Нужны уникальные ID записей для каждой затронутой позиции."
                )
            bindings[binding.position_id] = binding.entry_id
            identifiers.add(binding.entry_id)
        if set(bindings) != {row.route.position_id for row in execution.lines}:
            raise StockAdjustmentError(
                "Запись назначается каждой фактической позиции ровно один раз."
            )
        entries = []
        for row in execution.lines:
            route = row.route
            detail = route.adjustment
            position = by_position.get(route.position_id)
            if position is None or (
                position.dimensions,
                position.base_uom,
                position.on_hand_qty,
                position.version,
            ) != (
                detail.dimensions,
                row.base_uom,
                detail.expected_qty,
                route.expected_position_version,
            ):
                raise StockAdjustmentError(
                    "Позиция, версия, единица или исходное количество изменились до проведения."
                )
            quantity = QuantityVO(detail.quantity_delta.value.copy_abs())
            entries.append(
                StockLedgerEntry.create(
                    identifier=bindings[route.position_id],
                    position_id=route.position_id,
                    quantity_delta=detail.quantity_delta,
                    base_uom=row.base_uom,
                    conversion=QuantityConversionSnapshotVO(
                        quantity, row.base_uom, Decimal(1)
                    ),
                )
            )
        return tuple(entries)

    @staticmethod
    def application_snapshots(
        *, posting: StockPostingSnapshot, execution: StockAdjustmentExecutionSnapshot
    ) -> tuple[StockAdjustmentEntrySnapshot, ...]:
        """Проверяет весь Ledger и происхождение перед выдачей адресных поправок без потери целевого состояния."""
        if not isinstance(posting, StockPostingSnapshot) or not isinstance(
            execution, StockAdjustmentExecutionSnapshot
        ):
            raise StockAdjustmentError(
                "Нужны снимки проведения и фактической корректировки."
            )
        posting.ensure_valid()
        execution.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.ADJUSTMENT
            or posting.reversal_of_id is not None
            or posting.source.execution_id != execution.id
            or posting.posted_at < execution.executed_at
        ):
            raise StockAdjustmentError(
                "Проведение не соответствует исходному факту корректировки."
            )
        by_position = {entry.position_id: entry for entry in posting.entries}
        if set(by_position) != {row.route.position_id for row in execution.lines}:
            raise StockAdjustmentError(
                "Ledger должен покрывать ровно все позиции факта."
            )
        snapshots = []
        for row in execution.lines:
            entry = by_position[row.route.position_id]
            if (
                entry.base_uom != row.base_uom
                or entry.quantity_delta != row.route.adjustment.quantity_delta
                or entry.conversion.uom != row.base_uom
                or entry.conversion.factor_to_base != Decimal(1)
            ):
                raise StockAdjustmentError(
                    "Знак, количество или единица записи не совпадают с фактом."
                )
            snapshot = StockAdjustmentEntrySnapshot(
                posting.id, execution.id, entry.snapshot(), row.route
            )
            snapshot.ensure_valid()
            snapshots.append(snapshot)
        return tuple(snapshots)
