from typing import Protocol
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument


class StockDocumentRepositoryProtocol(Protocol):
    """Сохраняет корень и его строки в общей транзакции."""

    async def add(self, document: StockDocument) -> None:
        """Вставляет новый агрегат без самостоятельного commit."""
        ...

    async def get_for_update(
        self, identifier: StockDocumentIdVO
    ) -> StockDocument | None:
        """Блокирует корень, затем читает его полный актуальный состав."""
        ...

    async def save(self, document: StockDocument, *, expected_version: int) -> None:
        """Сохраняет существующий агрегат с защитой исходной версии без commit."""
        ...
