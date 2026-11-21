from dataclasses import replace

from src.modules.inventory.application.inventory_item.port.query_repository import (
    InventoryItemQueryRepositoryProtocol,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.dto import (
    ListInventoryItemsResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.error import (
    InvalidInventoryItemListQueryError,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.query import (
    ListInventoryItemsQuery,
)


class ListInventoryItemsHandler:
    """Читает страницу проекций через отдельный Application-порт."""

    def __init__(self, repository: InventoryItemQueryRepositoryProtocol) -> None:
        """Принимает порт чтения текущего tenant без доступа к SQL-сессии."""
        self._repository = repository

    async def execute(
        self, query: ListInventoryItemsQuery
    ) -> ListInventoryItemsResultDTO:
        """Проверяет пагинацию и нормализует поисковую строку до вызова порта."""
        if (
            type(query.offset) is not int
            or query.offset < 0
            or type(query.limit) is not int
            or not 1 <= query.limit <= 100
            or (query.search is not None and not isinstance(query.search, str))
        ):
            raise InvalidInventoryItemListQueryError(
                "Нужны offset >= 0, limit от 1 до 100 и строка поиска."
            )
        search = query.search.strip().casefold() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
