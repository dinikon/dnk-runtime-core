from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.error import (
    StockReceiptValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.receipt_valuation_snapshot import (
    StockReceiptValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockReceiptValuationPolicy:
    """Выделяет основание стоимости одной записи обычного прихода по историческим снимкам."""

    @staticmethod
    def build_snapshot(
        *,
        posting: StockPostingSnapshot,
        ledger_entry_id: StockLedgerEntryIdVO,
        position: StockPositionSnapshot,
        location: StockLocationSnapshot,
    ) -> StockReceiptValuationSnapshot:
        """Проверяет проведённый RECEIPT, выбранную положительную запись и идентичность позиции/локации без текущих настроек."""
        if (
            not isinstance(posting, StockPostingSnapshot)
            or not isinstance(ledger_entry_id, StockLedgerEntryIdVO)
            or not isinstance(position, StockPositionSnapshot)
            or not isinstance(location, StockLocationSnapshot)
        ):
            raise StockReceiptValuationSourceError(
                "Нужны снимок проведения, ID записи и специализированные снимки позиции/локации."
            )
        posting.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.RECEIPT
            or posting.reversal_of_id is not None
        ):
            raise StockReceiptValuationSourceError(
                "Закупочный слой строится только по обычному RECEIPT без компенсации."
            )
        entry = next(
            (row for row in posting.entries if row.id == ledger_entry_id), None
        )
        if entry is None or entry.quantity_delta.value <= 0:
            raise StockReceiptValuationSourceError(
                "Нужна существующая положительная запись выбранного поступления."
            )
        StockPostingPolicy.ensure_positions(entries=(entry,), positions=(position,))
        location.ensure_valid()
        if position.dimensions.location_id != location.id:
            raise StockReceiptValuationSourceError(
                "Локация не соответствует измерениям исходной позиции."
            )
        snapshot = StockReceiptValuationSnapshot(
            posting.id,
            entry.id,
            entry.position_id,
            position.dimensions.inventory_item_id,
            position.dimensions.owner_id,
            location.warehouse_id,
            entry.base_uom,
            QuantityVO(entry.quantity_delta.value),
            posting.posted_at,
        )
        snapshot.ensure_valid()
        return snapshot
