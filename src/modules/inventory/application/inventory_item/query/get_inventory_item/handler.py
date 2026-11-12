from src.modules.inventory.application.inventory_item.port.query_repository import (
    InventoryItemQueryRepositoryProtocol,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemResultDTO,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.query import (
    GetInventoryItemQuery,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError


class GetInventoryItemHandler:
    """Читает карточку через порт проекций без восстановления агрегата."""

    def __init__(self, repository: InventoryItemQueryRepositoryProtocol) -> None:
        """Принимает порт чтения с tenant-контекстом внешнего UoW."""
        self._repository = repository

    async def execute(self, query: GetInventoryItemQuery) -> GetInventoryItemResultDTO:
        """Возвращает проекцию либо сообщает об отсутствии позиции."""
        result = await self._repository.get_details(query)
        if result is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        return result
