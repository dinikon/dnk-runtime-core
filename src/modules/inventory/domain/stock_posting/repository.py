from typing import Protocol
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)


class StockPostingRepositoryProtocol(Protocol):
    """Добавляет и читает проведение вместе с неизменяемым Ledger."""

    async def add(self, posting: StockPosting) -> None:
        """Вставляет корень и Ledger на общей сессии."""
        ...

    async def get(self, identifier: StockPostingIdVO) -> StockPosting | None:
        """Восстанавливает полный исторический факт без текущих справочников."""
        ...
