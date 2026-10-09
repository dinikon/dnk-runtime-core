from src.modules.warehousing.application.warehouse.port.query_repository import (
    WarehouseQueryRepositoryProtocol,
)
from src.modules.warehousing.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseDetailsDTO,
)
from src.modules.warehousing.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.warehousing.domain.warehouse.error import WarehouseNotFoundError


class GetWarehouseHandler:
    """Читает карточку через порт проекций без восстановления агрегата."""

    def __init__(self, repository: WarehouseQueryRepositoryProtocol) -> None:
        """Принимает read repository общего tenant UoW."""
        self._repository = repository

    async def execute(self, query: GetWarehouseQuery) -> GetWarehouseDetailsDTO:
        """Возвращает карточку либо сообщает об отсутствии склада."""
        result = await self._repository.get_details(
            tenant_id=query.tenant_id,
            warehouse_id=query.warehouse_id,
        )
        if result is None:
            raise WarehouseNotFoundError("Склад не найден.")
        return result
