from typing import Protocol

from src.modules.inventory.domain.stock_location.aggregate import StockLocation


class StockLocationRepositoryProtocol(Protocol):
    """Определяет добавление самостоятельной локации в общей транзакции."""

    async def add(self, location: StockLocation) -> None:
        """Сохраняет новую локацию без самостоятельного commit."""
        ...
