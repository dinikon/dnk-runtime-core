from dataclasses import dataclass

from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockMovementEntryPairError,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)


@dataclass(frozen=True, slots=True)
class StockMovementEntryPairVO:
    """Явно сопоставляет полные расходную и приходную записи внутреннего перемещения."""

    outgoing_entry_id: StockLedgerEntryIdVO
    incoming_entry_id: StockLedgerEntryIdVO

    def __post_init__(self) -> None:
        """Проверяет собственные номинальные ссылки пары при создании значения."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует разные StockLedgerEntryIdVO без генерации ID или чтения проведения."""
        if (
            not isinstance(self.outgoing_entry_id, StockLedgerEntryIdVO)
            or not isinstance(self.incoming_entry_id, StockLedgerEntryIdVO)
            or self.outgoing_entry_id == self.incoming_entry_id
        ):
            raise InvalidStockMovementEntryPairError(
                "Нужны различные номинальные ID расходной и приходной записей Ledger."
            )
