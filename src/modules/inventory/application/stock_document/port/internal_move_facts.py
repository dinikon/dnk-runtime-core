from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.query import (
    ListInternalMoveDestinationsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.dto import (
    ListInternalMoveDestinationsResultDTO,
    InternalMoveDestinationDTO,
)
from typing import Protocol
from src.modules.inventory.application.stock_document.query.prepare_internal_move.query import (
    PrepareInternalMoveQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_internal_move.dto import (
    PrepareInternalMoveResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.query import (
    ListInternalMoveExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.dto import (
    ListInternalMoveExecutionsResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.query import (
    ListInternalMoveSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.dto import (
    ListInternalMoveSourcesResultDTO,
)


class InternalMoveFactsQueryPort(Protocol):
    """Читает подготовку, физические источники и историю INTERNAL_MOVE без восстановления агрегатов."""

    async def prepare(
        self, query: PrepareInternalMoveQuery
    ) -> PrepareInternalMoveResultDTO | None:
        """Возвращает согласованную версию и прогресс строк."""
        ...

    async def list_executions(
        self, query: ListInternalMoveExecutionsQuery
    ) -> ListInternalMoveExecutionsResultDTO | None:
        """Читает историю независимо от текущих количеств позиций."""
        ...

    async def sources(
        self, query: ListInternalMoveSourcesQuery
    ) -> ListInternalMoveSourcesResultDTO | None:
        """Ищет положительный запас; явный ID позволяет сверить и обнулённый источник."""
        ...

    async def destinations(
        self, query: ListInternalMoveDestinationsQuery
    ) -> ListInternalMoveDestinationsResultDTO | None:
        """Ищет допустимые адреса в складе документа, включая явную сверку выбранного ID."""
        ...
