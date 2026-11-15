from typing import Protocol
from src.modules.inventory.domain.stock_document.aggregate import StockDocument


class StockDocumentRepositoryProtocol(Protocol):
    """Сохраняет корень и его строки в общей транзакции."""

    async def add(self, document: StockDocument) -> None:
        """Вставляет новый агрегат без самостоятельного commit."""
        ...
