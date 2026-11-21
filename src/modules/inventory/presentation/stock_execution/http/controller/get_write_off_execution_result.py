from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.application.stock_execution.query.get_write_off_execution_result.query import (
    GetWriteOffExecutionResultQuery,
)
from src.modules.inventory.domain.stock_document.write_off_error import (
    WriteOffFactNotFoundError,
)
from src.modules.inventory.presentation.stock_execution.write_off_depends import (
    GetWriteOffExecutionResultHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_write_off_execution_result import (
    GetWriteOffExecutionResultResponse,
)


async def get_write_off_execution_result(
    identifier: UUID, handler: GetWriteOffExecutionResultHandlerDep
) -> GetWriteOffExecutionResultResponse:
    """Сериализует первоначальный результат без подмены нынешними остатками."""
    try:
        result = await handler.execute(GetWriteOffExecutionResultQuery(identifier))
    except WriteOffFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetWriteOffExecutionResultResponse.from_dto(result)
