from src.modules.inventory.application.stock_position.query.list_stock_balances.query import (
    ListStockBalancesQuery,
)
from src.modules.inventory.application.stock_position.query.list_stock_balances.dto import (
    ListStockBalancesResultDTO,
)
from typing import Protocol
from src.modules.inventory.application.stock_position.query.list_stock_positions.query import (
    ListStockPositionsQuery,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.dto import (
    ListStockPositionsResultDTO,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.query import (
    GetStockPositionQuery,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.dto import (
    GetStockPositionResultDTO,
)


class StockPositionQueryRepositoryProtocol(Protocol):
    """Определяет конкретные проекции чтения без ORM и команд изменения."""

    async def list(self, query: ListStockPositionsQuery) -> ListStockPositionsResultDTO:
        """Читает собственный результат сценария в текущем tenant."""
        ...

    async def get(
        self, query: GetStockPositionQuery
    ) -> GetStockPositionResultDTO | None:
        """Читает собственный результат сценария в текущем tenant."""
        ...

    async def balances(
        self, query: ListStockBalancesQuery
    ) -> ListStockBalancesResultDTO:
        """Читает сводку по измерениям с выбранной детализацией партий и серий."""
        ...
