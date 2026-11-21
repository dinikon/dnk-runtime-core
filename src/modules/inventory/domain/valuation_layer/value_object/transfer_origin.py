from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerTransferOriginError,
)
from src.modules.inventory.domain.valuation_layer.time import normalize_valuation_time
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.source import (
    ValuationLayerSourceVO,
)


@dataclass(frozen=True, slots=True)
class ValuationLayerTransferOriginVO:
    """Связывает производный слой с исходным слоем, закупочным приходом и выбытием при переносе."""

    parent_layer_id: ValuationLayerIdVO
    receipt_source: ValuationLayerSourceVO
    outgoing_entry_id: StockLedgerEntryIdVO
    moved_at: datetime

    def __post_init__(self) -> None:
        """Проверяет собственные ссылки и сохранённую дату перемещения."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует номинальные ссылки на слой и записи Ledger и момент перемещения в UTC."""
        if (
            not isinstance(self.parent_layer_id, ValuationLayerIdVO)
            or not isinstance(self.receipt_source, ValuationLayerSourceVO)
            or not isinstance(self.outgoing_entry_id, StockLedgerEntryIdVO)
        ):
            raise InvalidValuationLayerTransferOriginError(
                "Нужны ID исходного слоя, источник прихода и ID отрицательной записи."
            )
        self.receipt_source.ensure_valid()
        normalize_valuation_time(self.moved_at)
        if self.moved_at.utcoffset() != timedelta(0):
            raise InvalidValuationLayerTransferOriginError(
                "Время перемещения производного слоя должно храниться в UTC."
            )
