from typing import Protocol

from src.modules.inventory.domain.stock_lot.aggregate import StockLot


class StockLotRepositoryProtocol(Protocol):
    """Определяет сохранение самостоятельной партии в общей tenant-транзакции."""

    async def add(self, lot: StockLot) -> None:
        """Добавляет партию без commit или сообщает о занятом номере внутри SKU."""
        ...
