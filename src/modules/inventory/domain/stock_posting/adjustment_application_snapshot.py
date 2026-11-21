from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)


@dataclass(frozen=True, slots=True)
class StockAdjustmentApplicationLineSnapshot:
    """Фиксирует результат одной записи Ledger, а не состояние позиции в момент последующего чтения."""

    entry_id: StockLedgerEntryIdVO
    position: StockPositionCountingSnapshot

    def ensure_valid(self) -> None:
        """Требует типизированные ссылку записи и положительную версию результата применения."""
        if not isinstance(self.entry_id, StockLedgerEntryIdVO) or not isinstance(
            self.position, StockPositionCountingSnapshot
        ):
            raise StockAdjustmentError(
                "Нужны ID записи и снимок результата физической позиции."
            )
        self.position.ensure_valid()
        if self.position.version < 1:
            raise StockAdjustmentError(
                "Применение ненулевой поправки увеличивает версию позиции минимум до 1."
            )


@dataclass(frozen=True, slots=True)
class StockAdjustmentApplicationSnapshot:
    """Передаёт неизменяемый полный результат применения проведения без заявления о commit."""

    posting_id: StockPostingIdVO
    execution_id: StockExecutionIdVO
    applied_at: datetime
    lines: tuple[StockAdjustmentApplicationLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет происхождение, UTC и уникальность записей, позиций и физических измерений."""
        if (
            not isinstance(self.posting_id, StockPostingIdVO)
            or not isinstance(self.execution_id, StockExecutionIdVO)
            or not isinstance(self.applied_at, datetime)
            or self.applied_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise StockAdjustmentError(
                "Нужны происхождение, UTC-момент и непустой tuple результатов применения."
            )
        entries, positions, dimensions = set(), set(), set()
        for row in self.lines:
            if not isinstance(row, StockAdjustmentApplicationLineSnapshot):
                raise StockAdjustmentError(
                    "Нужны снимки результатов отдельных записей."
                )
            row.ensure_valid()
            if (
                row.entry_id in entries
                or row.position.id in positions
                or row.position.dimensions in dimensions
            ):
                raise StockAdjustmentError(
                    "Записи, позиции и измерения результата применения не повторяются."
                )
            entries.add(row.entry_id)
            positions.add(row.position.id)
            dimensions.add(row.position.dimensions)
