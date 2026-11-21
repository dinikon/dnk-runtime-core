from typing import Protocol
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)


class StockExecutionRepositoryProtocol(Protocol):
    """Добавляет и восстанавливает полный неизменяемый факт с собственными стоимостными основаниями."""

    async def add(self, execution: StockExecution) -> None:
        """Вставляет корень и принадлежащих ему детей без самостоятельного commit."""
        ...

    async def get(self, identifier: StockExecutionIdVO) -> StockExecution | None:
        """Возвращает полный сохранённый факт без новых событий и пересчёта."""
        ...
