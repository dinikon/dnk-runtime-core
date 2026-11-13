from dataclasses import replace
from src.modules.inventory.application.inventory_item.port.item_packaging_query_repository import (
    ItemPackagingQueryRepositoryProtocol,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.query import (
    ListItemPackagingsQuery,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.dto import (
    ListItemPackagingsResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError


class ListItemPackagingsHandler:
    """Выполняет чтение упаковок через отдельный порт проекций."""

    def __init__(self, repository: ItemPackagingQueryRepositoryProtocol) -> None:
        """Принимает read-порт без зависимости от SQLAlchemy или UoW."""
        self._repository = repository

    async def execute(
        self, query: ListItemPackagingsQuery
    ) -> ListItemPackagingsResultDTO:
        """Возвращает конкретный результат чтения или предметную ошибку отсутствия."""
        if not await self._repository.item_exists(query.inventory_item_id):
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        search = query.search.strip() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
