from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.query import (
    GetIssueExecutionResultQuery,
)
from src.modules.inventory.domain.stock_document.issue_error import (
    IssueFactNotFoundError,
)
from src.modules.inventory.presentation.stock_execution.issue_depends import (
    GetIssueExecutionResultHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_issue_execution_result import (
    GetIssueExecutionResultResponse,
)


async def get_issue_execution_result(
    identifier: UUID, handler: GetIssueExecutionResultHandlerDep
) -> GetIssueExecutionResultResponse:
    """Сериализует первоначальный результат без подмены нынешними остатками."""
    try:
        result = await handler.execute(GetIssueExecutionResultQuery(identifier))
    except IssueFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetIssueExecutionResultResponse.from_dto(result)
