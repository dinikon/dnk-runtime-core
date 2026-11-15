from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.query import (
    GetStatusChangeExecutionResultQuery,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    StatusChangeFactNotFoundError,
)
from src.modules.inventory.presentation.stock_execution.status_change_depends import (
    GetStatusChangeExecutionResultHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_status_change_execution_result import (
    GetStatusChangeExecutionResultResponse,
)


async def get_status_change_execution_result(
    identifier: UUID, handler: GetStatusChangeExecutionResultHandlerDep
) -> GetStatusChangeExecutionResultResponse:
    """Сериализует первоначальный результат без подмены нынешними остатками."""
    try:
        result = await handler.execute(GetStatusChangeExecutionResultQuery(identifier))
    except StatusChangeFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetStatusChangeExecutionResultResponse.from_dto(result)
