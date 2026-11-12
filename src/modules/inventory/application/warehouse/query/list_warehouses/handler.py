from dataclasses import replace

from src.modules.inventory.application.warehouse.port.query_repository import (
    WarehouseQueryRepositoryProtocol,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.dto import (
    ListWarehousesResultDTO,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListQueryError,
)


class ListWarehousesHandler:
    """Проверяет параметры чтения и делегирует запрос read-порту."""

    def __init__(self, repository: WarehouseQueryRepositoryProtocol) -> None:
        """Принимает порт проекций текущего tenant."""
        self._repository = repository

    async def execute(self, query: ListWarehousesQuery) -> ListWarehousesResultDTO:
        """Нормализует пробелы поиска и проверяет пагинацию и bool активности."""
        if (
            type(query.offset) is not int
            or query.offset < 0
            or type(query.limit) is not int
            or not 1 <= query.limit <= 100
            or (query.search is not None and not isinstance(query.search, str))
            or (query.is_active is not None and type(query.is_active) is not bool)
        ):
            raise InvalidWarehouseListQueryError(
                "Нужны offset >= 0, limit от 1 до 100, строка поиска и bool активности."
            )
        search = query.search.strip() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
