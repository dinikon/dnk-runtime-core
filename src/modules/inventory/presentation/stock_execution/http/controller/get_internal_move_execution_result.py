from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.query import (
    GetInternalMoveExecutionResultQuery,
)
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMoveFactNotFoundError,
)
from src.modules.inventory.presentation.stock_execution.internal_move_depends import (
    GetInternalMoveExecutionResultHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_internal_move_execution_result import (
    GetInternalMoveExecutionResultResponse,
)


async def get_internal_move_execution_result(
    identifier: UUID, handler: GetInternalMoveExecutionResultHandlerDep
) -> GetInternalMoveExecutionResultResponse:
    """Сериализует первоначальный результат без подмены нынешними остатками."""
    try:
        result = await handler.execute(GetInternalMoveExecutionResultQuery(identifier))
    except InternalMoveFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetInternalMoveExecutionResultResponse.from_dto(result)
