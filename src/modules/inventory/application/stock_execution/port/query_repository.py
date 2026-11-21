from typing import Protocol
from src.modules.inventory.application.stock_execution.query.list_stock_executions.query import (
    ListStockExecutionsQuery,
)
from src.modules.inventory.application.stock_execution.query.list_stock_executions.dto import (
    ListStockExecutionsResultDTO,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.query import (
    GetStockExecutionDetailsQuery,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.dto import (
    GetStockExecutionDetailsResultDTO,
)


class StockExecutionQueryRepositoryProtocol(Protocol):
    """Определяет конкретные проекции чтения без ORM и команд изменения."""

    async def list(
        self, query: ListStockExecutionsQuery
    ) -> ListStockExecutionsResultDTO:
        """Читает собственный результат сценария в текущем tenant."""
        ...

    async def details(
        self, query: GetStockExecutionDetailsQuery
    ) -> GetStockExecutionDetailsResultDTO | None:
        """Читает собственный результат сценария в текущем tenant."""
        ...
