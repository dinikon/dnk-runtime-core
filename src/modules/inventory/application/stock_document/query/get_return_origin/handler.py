from src.modules.inventory.application.stock_document.query.get_return_origin.query import (
    GetReturnOriginQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_origin.dto import (
    GetReturnOriginResultDTO,
)
from src.modules.inventory.application.stock_document.port.return_origin import (
    ReturnOriginPort,
)
from src.modules.inventory.application.stock_document.port.return_origin_query import (
    ReturnOriginQueryPort,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.policy.stock_return import StockReturnPolicy


class GetReturnOriginHandler:
    """Проверяет бизнес-допустимость основания и читает отдельную проекцию интерфейса."""

    def __init__(self, origin: ReturnOriginPort, reader: ReturnOriginQueryPort) -> None:
        """Принимает бизнес-справку и порт конкретной read-модели."""
        self._origin, self._reader = origin, reader

    async def execute(self, query: GetReturnOriginQuery) -> GetReturnOriginResultDTO:
        """Не блокирует исходный факт и не резервирует показываемые количества."""
        origin = await self._origin.get(
            StockExecutionIdVO(query.execution_id), lock=False
        )
        if origin is None:
            raise StockDocumentNotFoundError("Исходное исполнение не найдено.")
        direction = StockReturnPolicy.direction(origin)
        result = await self._reader.get(query, direction=direction.value)
        if result is None:
            raise StockDocumentNotFoundError("Исходное исполнение не найдено.")
        return result
