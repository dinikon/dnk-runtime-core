from src.modules.inventory.application.stock_document.query.list_return_destinations.query import (
    ListReturnDestinationsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_destinations.dto import (
    ListReturnDestinationsResultDTO,
)
from typing import Protocol
from src.modules.inventory.application.stock_document.query.prepare_return.query import (
    PrepareReturnQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_return.dto import (
    PrepareReturnResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.query import (
    ListReturnExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.dto import (
    ListReturnExecutionsResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.query import (
    ListReturnSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.dto import (
    ListReturnSourcesResultDTO,
)


class ReturnFactsQueryPort(Protocol):
    """Читает подготовку, физические источники и историю RETURN без восстановления агрегатов."""

    async def prepare(self, query: PrepareReturnQuery) -> PrepareReturnResultDTO | None:
        """Возвращает согласованную версию и прогресс строк."""
        ...

    async def list_executions(
        self, query: ListReturnExecutionsQuery
    ) -> ListReturnExecutionsResultDTO | None:
        """Читает историю независимо от текущих количеств позиций."""
        ...

    async def sources(
        self, query: ListReturnSourcesQuery
    ) -> ListReturnSourcesResultDTO | None:
        """Ищет положительный запас; явный ID позволяет сверить и обнулённый источник."""
        ...

    async def destinations(
        self, query: ListReturnDestinationsQuery
    ) -> ListReturnDestinationsResultDTO | None:
        """Ищет активные адреса приёмки внутри склада возврата."""
        ...
