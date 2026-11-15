from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.handler import (
    GetStatusChangeExecutionResultHandler,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.status_change_result_repository import (
    SqlAlchemyStatusChangeExecutionResultRepository,
)


def get_status_change_execution_result_handler(
    uow: UoWDep,
) -> GetStatusChangeExecutionResultHandler:
    """Собирает чтение результата на tenant-сессии общего UoW."""
    return GetStatusChangeExecutionResultHandler(
        SqlAlchemyStatusChangeExecutionResultRepository(uow.session)
    )


GetStatusChangeExecutionResultHandlerDep = Annotated[
    GetStatusChangeExecutionResultHandler,
    Depends(get_status_change_execution_result_handler),
]
