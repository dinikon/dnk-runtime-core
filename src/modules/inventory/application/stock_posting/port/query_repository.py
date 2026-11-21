from typing import Protocol
from src.modules.inventory.application.stock_posting.query.list_stock_movements.query import (
    ListStockMovementsQuery,
)
from src.modules.inventory.application.stock_posting.query.list_stock_movements.dto import (
    ListStockMovementsResultDTO,
)
from src.modules.inventory.application.stock_posting.query.list_stock_postings.query import (
    ListStockPostingsQuery,
)
from src.modules.inventory.application.stock_posting.query.list_stock_postings.dto import (
    ListStockPostingsResultDTO,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.query import (
    GetStockPostingDetailsQuery,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.dto import (
    GetStockPostingDetailsResultDTO,
)


class StockPostingQueryRepositoryProtocol(Protocol):
    """Определяет конкретные проекции чтения без ORM и команд изменения."""

    async def movements(
        self, query: ListStockMovementsQuery
    ) -> ListStockMovementsResultDTO:
        """Читает собственный результат сценария в текущем tenant."""
        ...

    async def list(self, query: ListStockPostingsQuery) -> ListStockPostingsResultDTO:
        """Читает собственный результат сценария в текущем tenant."""
        ...

    async def details(
        self, query: GetStockPostingDetailsQuery
    ) -> GetStockPostingDetailsResultDTO | None:
        """Читает собственный результат сценария в текущем tenant."""
        ...
