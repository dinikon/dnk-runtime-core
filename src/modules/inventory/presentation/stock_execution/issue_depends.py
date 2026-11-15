from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.handler import (
    GetIssueExecutionResultHandler,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.issue_result_repository import (
    SqlAlchemyIssueExecutionResultRepository,
)


def get_issue_execution_result_handler(uow: UoWDep) -> GetIssueExecutionResultHandler:
    """Собирает чтение результата на tenant-сессии общего UoW."""
    return GetIssueExecutionResultHandler(
        SqlAlchemyIssueExecutionResultRepository(uow.session)
    )


GetIssueExecutionResultHandlerDep = Annotated[
    GetIssueExecutionResultHandler, Depends(get_issue_execution_result_handler)
]
