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
        if type(query.limit) is not int or not 1 <= query.limit <= 200:
            raise ValueError("limit must be between 1 and 200.")
        if type(query.offset) is not int or query.offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        return ListSkusResultDTO(
            tuple(
                await self._repository.list_details(
                    limit=query.limit,
                    offset=query.offset,
                )
            )
        )
