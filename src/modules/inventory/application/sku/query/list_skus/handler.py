from src.modules.inventory.application.sku.port.query_repository import (
    SkuQueryRepositoryProtocol,
)
from src.modules.inventory.application.sku.query.list_skus.dto import ListSkusResultDTO
from src.modules.inventory.application.sku.query.list_skus.query import ListSkusQuery


class ListSkusHandler:
    """Читает страницу проекций SKU через read-side порт."""

    def __init__(self, repository: SkuQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: ListSkusQuery) -> ListSkusResultDTO:
        """Возвращает ограниченную страницу текущего tenant."""
        return ListSkusResultDTO(
            tuple(
                await self._repository.list_details(
                    limit=query.limit,
                    offset=query.offset,
                )
            )
        )
