from dataclasses import replace
from src.modules.inventory.application.stock_position.port.query_repository import (
    StockPositionQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.query import (
    GetStockPositionQuery,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.dto import (
    GetStockPositionResultDTO,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


class GetStockPositionHandler:
    """Читает собственную проекцию и пакетно дополняет её публичными именами CRM."""

    def __init__(
        self,
        repository: StockPositionQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает независимые read-порты общей tenant-транзакции."""
        self._repository, self._owners = repository, owners

    async def execute(self, query: GetStockPositionQuery) -> GetStockPositionResultDTO:
        """Возвращает точные количества без восстановления агрегатов и без N+1."""
        result = await self._repository.get(query)
        if result is None:
            raise ReceiptFactNotFoundError("Физическая позиция не найдена.")
        owners = await self._owners.get_many((result.owner_id,))
        owner = owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner else None)
