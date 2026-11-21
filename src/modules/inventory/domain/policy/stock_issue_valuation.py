from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.error import (
    StockIssueValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockIssueValuationPolicy:
    """Выделяет проверенное основание потребления стоимости одной записи обычного ISSUE."""

    @staticmethod
    def build_snapshot(
        *,
        posting: StockPostingSnapshot,
        ledger_entry_id: StockLedgerEntryIdVO,
        position: StockPositionSnapshot,
        location: StockLocationSnapshot,
    ) -> StockIssueValuationSnapshot:
        """Проверяет отрицательную запись, позицию и локацию, сохраняя историческое базовое количество."""
        if (
            not isinstance(posting, StockPostingSnapshot)
            or not isinstance(ledger_entry_id, StockLedgerEntryIdVO)
            or not isinstance(position, StockPositionSnapshot)
            or not isinstance(location, StockLocationSnapshot)
        ):
            raise StockIssueValuationSourceError(
                "Нужны снимок проведения, ID записи и специализированные снимки позиции/локации."
            )
        posting.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.ISSUE
            or posting.reversal_of_id is not None
        ):
            raise StockIssueValuationSourceError(
                "Слой потребляется только по обычному ISSUE без компенсации."
            )
        entry = next(
            (row for row in posting.entries if row.id == ledger_entry_id), None
        )
        if entry is None or entry.quantity_delta.value >= 0:
            raise StockIssueValuationSourceError(
                "Нужна существующая отрицательная запись выбранного расхода."
            )
        StockPostingPolicy.ensure_positions(entries=(entry,), positions=(position,))
        location.ensure_valid()
        if position.dimensions.location_id != location.id:
            raise StockIssueValuationSourceError(
                "Локация не соответствует измерениям расходной позиции."
            )
        snapshot = StockIssueValuationSnapshot(
            posting.id,
            entry.id,
            entry.position_id,
            position.dimensions.inventory_item_id,
            position.dimensions.owner_id,
            location.warehouse_id,
            entry.base_uom,
            QuantityVO(entry.quantity_delta.value.copy_abs()),
            posting.posted_at,
            position.dimensions.serial_id,
        )
        snapshot.ensure_valid()
        return snapshot
