from dataclasses import dataclass

from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerSourceError,
)


@dataclass(frozen=True, slots=True)
class ValuationLayerSourceVO:
    """Сохраняет ссылки на конкретную запись прихода и её исходную позицию без чужих агрегатов."""

    posting_id: StockPostingIdVO
    ledger_entry_id: StockLedgerEntryIdVO
    position_id: StockPositionIdVO

    def __post_init__(self) -> None:
        """Проверяет собственные номинальные идентификаторы без поиска источника в хранении."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Запрещает сырые UUID и идентификаторы других видов вместо ссылок прихода."""
        if (
            not isinstance(self.posting_id, StockPostingIdVO)
            or not isinstance(self.ledger_entry_id, StockLedgerEntryIdVO)
            or not isinstance(self.position_id, StockPositionIdVO)
        ):
            raise InvalidValuationLayerSourceError(
                "Нужны StockPostingIdVO, StockLedgerEntryIdVO и StockPositionIdVO."
            )
