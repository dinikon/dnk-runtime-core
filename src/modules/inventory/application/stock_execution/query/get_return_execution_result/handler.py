from src.modules.inventory.application.stock_execution.port.return_result_repository import (
    ReturnExecutionResultRepositoryProtocol,
)
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.query import (
    GetReturnExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.dto import (
    GetReturnExecutionResultDTO,
)
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnFactNotFoundError,
)


class GetReturnExecutionResultHandler:
    """Возвращает исторические источники, дельты и исходные количества до/после."""

    def __init__(self, repository: ReturnExecutionResultRepositoryProtocol) -> None:
        """Получает независимый read-порт собственного результата."""
        self._repository = repository

    async def execute(
        self, query: GetReturnExecutionResultQuery
    ) -> GetReturnExecutionResultDTO:
        """Отличает отсутствующий факт от сохранённого первоначального ответа."""
        result = await self._repository.get(query)
        if result is None:
            raise ReturnFactNotFoundError("Результат возврата не найден.")
        return result
