from dataclasses import replace
from src.modules.inventory.application.stock_position.port.query_repository import (
    StockPositionQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.query import (
    ListStockPositionsQuery,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.dto import (
    ListStockPositionsResultDTO,
)


class ListStockPositionsHandler:
    """Читает собственную проекцию и пакетно дополняет её публичными именами CRM."""

    def __init__(
        self,
        repository: StockPositionQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает независимые read-порты общей tenant-транзакции."""
        self._repository, self._owners = repository, owners

    async def execute(
        self, query: ListStockPositionsQuery
    ) -> ListStockPositionsResultDTO:
        """Возвращает точные количества без восстановления агрегатов и без N+1."""
        result = await self._repository.list(query)
        owners = await self._owners.get_many(
            tuple(dict.fromkeys(item.owner_id for item in result.items))
        )
        return replace(
            result,
            items=tuple(
                replace(
                    item,
                    owner_name=(
                        owners[item.owner_id].name if item.owner_id in owners else None
                    ),
                )
                for item in result.items
            ),
        )
