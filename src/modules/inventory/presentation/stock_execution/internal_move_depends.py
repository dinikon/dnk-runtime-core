from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.handler import (
    GetInternalMoveExecutionResultHandler,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.internal_move_result_repository import (
    SqlAlchemyInternalMoveExecutionResultRepository,
)


def get_internal_move_execution_result_handler(
    uow: UoWDep,
) -> GetInternalMoveExecutionResultHandler:
    """Собирает чтение результата на tenant-сессии общего UoW."""
    return GetInternalMoveExecutionResultHandler(
        SqlAlchemyInternalMoveExecutionResultRepository(uow.session)
    )


GetInternalMoveExecutionResultHandlerDep = Annotated[
    GetInternalMoveExecutionResultHandler,
    Depends(get_internal_move_execution_result_handler),
]
