from src.modules.inventory.application.warehouse.port.query_repository import (
    WarehouseQueryRepositoryProtocol,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseResultDTO,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError


class GetWarehouseHandler:
    """Читает карточку через порт проекций."""

    def __init__(self, repository: WarehouseQueryRepositoryProtocol) -> None:
        """Принимает read-порт без доступа к сессии."""
        self._repository = repository

    async def execute(self, query: GetWarehouseQuery) -> GetWarehouseResultDTO:
        """Возвращает карточку либо предметную ошибку отсутствующего склада."""
        result = await self._repository.get_details(query)
        if result is None:
            raise WarehouseNotFoundError("Склад не найден.")
        return result
