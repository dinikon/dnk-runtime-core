from typing import Protocol
from src.modules.inventory.application.stock_document.query.prepare_status_change.query import (
    PrepareStatusChangeQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_status_change.dto import (
    PrepareStatusChangeResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.query import (
    ListStatusChangeExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.dto import (
    ListStatusChangeExecutionsResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_status_change_sources.query import (
    ListStatusChangeSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_sources.dto import (
    ListStatusChangeSourcesResultDTO,
)


class StatusChangeFactsQueryPort(Protocol):
    """Читает подготовку, физические источники и историю STATUS_CHANGE без восстановления агрегатов."""

    async def prepare(
        self, query: PrepareStatusChangeQuery
    ) -> PrepareStatusChangeResultDTO | None:
        """Возвращает согласованную версию и прогресс строк."""
        ...

    async def list_executions(
        self, query: ListStatusChangeExecutionsQuery
    ) -> ListStatusChangeExecutionsResultDTO | None:
        """Читает историю независимо от текущих количеств позиций."""
        ...

    async def sources(
        self, query: ListStatusChangeSourcesQuery
    ) -> ListStatusChangeSourcesResultDTO | None:
        """Ищет положительный запас; явный ID позволяет сверить и обнулённый источник."""
        ...
