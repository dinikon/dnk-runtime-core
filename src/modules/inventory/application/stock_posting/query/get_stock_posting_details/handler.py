from dataclasses import replace
from src.modules.inventory.application.stock_posting.port.query_repository import (
    StockPostingQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.query import (
    GetStockPostingDetailsQuery,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.dto import (
    GetStockPostingDetailsResultDTO,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


class GetStockPostingDetailsHandler:
    """Читает нормализованный факт и дополняет его именем владельца через публичный порт."""

    def __init__(
        self,
        repository: StockPostingQueryRepositoryProtocol,
        owners: StockOwnerReferencePort,
    ) -> None:
        """Принимает read-порты одного tenant-UoW."""
        self._repository, self._owners = repository, owners

    async def execute(
        self, query: GetStockPostingDetailsQuery
    ) -> GetStockPostingDetailsResultDTO:
        """Возвращает факт даже при отсутствии сохранённого результата команды."""
        result = await self._repository.details(query)
        if result is None:
            raise ReceiptFactNotFoundError("Учётный факт не найден.")
        owners = await self._owners.get_many((result.owner_id,))
        owner = owners.get(result.owner_id)
        return replace(result, owner_name=owner.name if owner else None)
