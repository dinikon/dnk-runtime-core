from dataclasses import dataclass

from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockPostingEntryBindingError,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)


@dataclass(frozen=True, slots=True)
class StockPostingEntryBindingVO:
    """Связывает итоговую позицию с явно переданным идентификатором записи журнала."""

    position_id: StockPositionIdVO
    entry_id: StockLedgerEntryIdVO

    def __post_init__(self) -> None:
        """Требует типизированные ссылки без генерации ID внутри Domain."""
        if not isinstance(self.position_id, StockPositionIdVO) or not isinstance(
            self.entry_id, StockLedgerEntryIdVO
        ):
            raise InvalidStockPostingEntryBindingError(
                "Нужны StockPositionIdVO и StockLedgerEntryIdVO для каждой итоговой позиции."
            )
