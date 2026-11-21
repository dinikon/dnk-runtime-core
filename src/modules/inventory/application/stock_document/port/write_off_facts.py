from typing import Protocol
from src.modules.inventory.application.stock_document.query.prepare_write_off.query import (
    PrepareWriteOffQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_write_off.dto import (
    PrepareWriteOffResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_write_off_executions.query import (
    ListWriteOffExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_executions.dto import (
    ListWriteOffExecutionsResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_write_off_sources.query import (
    ListWriteOffSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_sources.dto import (
    ListWriteOffSourcesResultDTO,
)


class WriteOffFactsQueryPort(Protocol):
    """Читает подготовку, физические источники и историю WRITE_OFF без восстановления агрегатов."""

    async def prepare(
        self, query: PrepareWriteOffQuery
    ) -> PrepareWriteOffResultDTO | None:
        """Возвращает согласованную версию и прогресс строк."""
        ...

    async def list_executions(
        self, query: ListWriteOffExecutionsQuery
    ) -> ListWriteOffExecutionsResultDTO | None:
        """Читает историю независимо от текущих количеств позиций."""
        ...

    async def sources(
        self, query: ListWriteOffSourcesQuery
    ) -> ListWriteOffSourcesResultDTO | None:
        """Ищет положительный запас; явный ID позволяет сверить и обнулённый источник."""
        ...
