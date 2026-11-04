from dataclasses import dataclass

from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockLedgerEntrySnapshotError,
    ZeroStockLedgerDeltaError,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockLedgerEntrySnapshot:
    """Передаёт целевую позицию, единицу и ненулевую дельту записи без Entity и исходного пересчёта."""

    id: StockLedgerEntryIdVO
    position_id: StockPositionIdVO
    quantity_delta: StockDeltaVO
    base_uom: UomCodeVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, известную единицу и запрет нулевого движения."""
        if (
            not isinstance(self.id, StockLedgerEntryIdVO)
            or not isinstance(self.position_id, StockPositionIdVO)
            or not isinstance(self.quantity_delta, StockDeltaVO)
            or not isinstance(self.base_uom, UomCodeVO)
        ):
            raise InvalidStockLedgerEntrySnapshotError(
                "Нужны типизированные ID записи и позиции, дельта и базовая единица."
            )
        get_uom(self.base_uom)
        if self.quantity_delta.value.is_zero():
            raise ZeroStockLedgerDeltaError(
                "Нулевая запись Ledger не применяется к позиции."
            )
