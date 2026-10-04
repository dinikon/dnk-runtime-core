from src.modules.inventory.application.sku.port.query_repository import (
    SkuQueryRepositoryProtocol,
)
from src.modules.inventory.application.sku.query.get_sku.dto import SkuDetailsDTO
from src.modules.inventory.application.sku.query.get_sku.query import GetSkuQuery
from src.modules.inventory.domain.sku.error import SkuNotFoundError


class GetSkuHandler:
    """Читает проекцию SKU без восстановления агрегата."""

    def __init__(self, repository: SkuQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: GetSkuQuery) -> SkuDetailsDTO:
        """Возвращает SKU либо сообщает об отсутствии в текущем tenant."""
        result = await self._repository.get_details(sku_id=query.sku_id)
        if result is None:
            raise SkuNotFoundError("SKU not found.")
        return result
