from src.modules.inventory.application.stock_execution.port.write_off_result_repository import (
    WriteOffExecutionResultRepositoryProtocol,
)
from src.modules.inventory.application.stock_execution.query.get_write_off_execution_result.query import (
    GetWriteOffExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_write_off_execution_result.dto import (
    GetWriteOffExecutionResultDTO,
)
from src.modules.inventory.domain.stock_document.write_off_error import (
    WriteOffFactNotFoundError,
)


class GetWriteOffExecutionResultHandler:
    """Возвращает исторические источники, дельты и исходные количества до/после."""

    def __init__(self, repository: WriteOffExecutionResultRepositoryProtocol) -> None:
        """Получает независимый read-порт собственного результата."""
        self._repository = repository

    async def execute(
        self, query: GetWriteOffExecutionResultQuery
    ) -> GetWriteOffExecutionResultDTO:
        """Отличает отсутствующий факт от сохранённого первоначального ответа."""
        result = await self._repository.get(query)
        if result is None:
            raise WriteOffFactNotFoundError("Результат списания не найден.")
        return result
