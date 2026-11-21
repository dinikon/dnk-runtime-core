from src.modules.inventory.application.stock_execution.port.status_change_result_repository import (
    StatusChangeExecutionResultRepositoryProtocol,
)
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.query import (
    GetStatusChangeExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.dto import (
    GetStatusChangeExecutionResultDTO,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    StatusChangeFactNotFoundError,
)


class GetStatusChangeExecutionResultHandler:
    """Возвращает исторические источники, дельты и исходные количества до/после."""

    def __init__(
        self, repository: StatusChangeExecutionResultRepositoryProtocol
    ) -> None:
        """Получает независимый read-порт собственного результата."""
        self._repository = repository

    async def execute(
        self, query: GetStatusChangeExecutionResultQuery
    ) -> GetStatusChangeExecutionResultDTO:
        """Отличает отсутствующий факт от сохранённого первоначального ответа."""
        result = await self._repository.get(query)
        if result is None:
            raise StatusChangeFactNotFoundError(
                "Результат изменения состояния не найден."
            )
        return result
