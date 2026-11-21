from dataclasses import replace
from src.modules.inventory.application.stock_execution.port.query_repository import (
    StockExecutionQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.query import (
    GetStockExecutionDetailsQuery,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.dto import (
    GetStockExecutionDetailsResultDTO,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


class GetStockExecutionDetailsHandler:
    """Читает нормализованный факт и дополняет его именем владельца через публичный порт."""

    def __init__(
        self,
        repository: StockExecutionQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты одного tenant-UoW."""
        self._repository, self._owners = repository, owners

    async def execute(
        self, query: GetStockExecutionDetailsQuery
    ) -> GetStockExecutionDetailsResultDTO:
        """Возвращает факт даже при отсутствии сохранённого результата команды."""
        result = await self._repository.details(query)
        if result is None:
            raise ReceiptFactNotFoundError("Учётный факт не найден.")
        owners = await self._owners.get_many((result.owner_id,))
        owner = owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner else None)
