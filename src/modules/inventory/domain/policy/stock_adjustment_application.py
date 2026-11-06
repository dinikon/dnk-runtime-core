from datetime import datetime

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.policy.stock_adjustment_posting import (
    StockAdjustmentPostingPolicy,
)
from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_execution.adjustment_snapshot import (
    StockAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_posting.adjustment_application_snapshot import (
    StockAdjustmentApplicationSnapshot,
    StockAdjustmentApplicationLineSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot


class StockAdjustmentApplicationPolicy:
    """Сопоставляет полный Ledger с полученными состояниями позиций без повторного применения или I/O."""

    @staticmethod
    def build_snapshot(
        *,
        posting: StockPostingSnapshot,
        execution: StockAdjustmentExecutionSnapshot,
        positions_after: tuple[StockPositionCountingSnapshot, ...],
        applied_at: datetime,
    ) -> StockAdjustmentApplicationSnapshot:
        """Фиксирует ровно целевые количества/измерения и одну следующую версию каждой применённой записи."""
        entries = StockAdjustmentPostingPolicy.application_snapshots(
            posting=posting, execution=execution
        )
        normalized = StockPostingPolicy.normalize_time(applied_at)
        if normalized < posting.posted_at:
            raise StockAdjustmentError("Применение не может предшествовать проведению.")
        if not isinstance(positions_after, tuple):
            raise StockAdjustmentError(
                "Нужен tuple результатов только затронутых позиций."
            )
        by_position = {}
        for position in positions_after:
            if not isinstance(position, StockPositionCountingSnapshot):
                raise StockAdjustmentError(
                    "Нужны снимки количества и версии результатов применения."
                )
            position.ensure_valid()
            if position.id in by_position:
                raise StockAdjustmentError("Результат позиции повторяется.")
            by_position[position.id] = position
        if set(by_position) != {snapshot.entry.position_id for snapshot in entries}:
            raise StockAdjustmentError(
                "Нужны результаты всех и только затронутых Ledger позиций."
            )
        rows = []
        for snapshot in entries:
            position = by_position[snapshot.entry.position_id]
            if (
                position.dimensions != snapshot.route.adjustment.dimensions
                or position.base_uom != snapshot.entry.base_uom
                or position.on_hand_qty != snapshot.route.adjustment.target_qty
                or position.version != snapshot.route.expected_position_version + 1
            ):
                raise StockAdjustmentError(
                    "Результат не совпадает с целевыми измерениями, количеством или следующей версией позиции."
                )
            rows.append(
                StockAdjustmentApplicationLineSnapshot(snapshot.entry.id, position)
            )
        result = StockAdjustmentApplicationSnapshot(
            posting.id,
            execution.id,
            normalized,
            tuple(sorted(rows, key=lambda row: row.entry_id.uuid.int)),
        )
        result.ensure_valid()
        return result

    @staticmethod
    def ensure_compatible(
        *,
        application: StockAdjustmentApplicationSnapshot,
        posting: StockPostingSnapshot,
        execution: StockAdjustmentExecutionSnapshot,
    ) -> None:
        """Заново сопоставляет сохранённые результаты с полным неизменяемым фактом и Ledger, независимо от порядка строк."""
        if not isinstance(application, StockAdjustmentApplicationSnapshot):
            raise StockAdjustmentError(
                "Нужен результат применения; планируемая запись Ledger его не заменяет."
            )
        application.ensure_valid()
        expected = StockAdjustmentApplicationPolicy.build_snapshot(
            posting=posting,
            execution=execution,
            positions_after=tuple(row.position for row in application.lines),
            applied_at=application.applied_at,
        )
        if (
            application.posting_id != expected.posting_id
            or application.execution_id != expected.execution_id
            or {row.entry_id: row.position for row in application.lines}
            != {row.entry_id: row.position for row in expected.lines}
        ):
            raise StockAdjustmentError(
                "Результаты применения относятся к другим записям, проведению или исполнению."
            )
