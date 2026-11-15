from src.modules.inventory.application.stock_execution.port.internal_move_result_repository import (
    InternalMoveExecutionResultRepositoryProtocol,
)
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.query import (
    GetInternalMoveExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.dto import (
    GetInternalMoveExecutionResultDTO,
)
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMoveFactNotFoundError,
)


class GetInternalMoveExecutionResultHandler:
    """Возвращает исторические источники, дельты и исходные количества до/после."""

    def __init__(
        self, repository: InternalMoveExecutionResultRepositoryProtocol
    ) -> None:
        """Получает независимый read-порт собственного результата."""
        self._repository = repository

    async def execute(
        self, query: GetInternalMoveExecutionResultQuery
    ) -> GetInternalMoveExecutionResultDTO:
        """Отличает отсутствующий факт от сохранённого первоначального ответа."""
        result = await self._repository.get(query)
        if result is None:
            raise InternalMoveFactNotFoundError("Результат перемещения не найден.")
        return result
