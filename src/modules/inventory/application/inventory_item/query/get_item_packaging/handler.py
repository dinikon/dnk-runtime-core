from src.modules.inventory.application.inventory_item.port.item_packaging_query_repository import (
    ItemPackagingQueryRepositoryProtocol,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.query import (
    GetItemPackagingQuery,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.dto import (
    GetItemPackagingResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemComponentNotFoundError,
)


class GetItemPackagingHandler:
    """Выполняет чтение упаковок через отдельный порт проекций."""

    def __init__(self, repository: ItemPackagingQueryRepositoryProtocol) -> None:
        """Принимает read-порт без зависимости от SQLAlchemy или UoW."""
        self._repository = repository

    async def execute(self, query: GetItemPackagingQuery) -> GetItemPackagingResultDTO:
        """Возвращает конкретный результат чтения или предметную ошибку отсутствия."""
        result = await self._repository.get_details(query)
        if result is None:
            raise InventoryItemComponentNotFoundError("Упаковка отсутствует в позиции.")
        return result
