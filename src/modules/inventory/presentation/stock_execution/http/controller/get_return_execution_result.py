from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.query import (
    GetReturnExecutionResultQuery,
)
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnFactNotFoundError,
)
from src.modules.inventory.presentation.stock_execution.return_depends import (
    GetReturnExecutionResultHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_return_execution_result import (
    GetReturnExecutionResultResponse,
)


async def get_return_execution_result(
    identifier: UUID, handler: GetReturnExecutionResultHandlerDep
) -> GetReturnExecutionResultResponse:
    """Сериализует первоначальный результат без подмены нынешними остатками."""
    try:
        result = await handler.execute(GetReturnExecutionResultQuery(identifier))
    except ReturnFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetReturnExecutionResultResponse.from_dto(result)
