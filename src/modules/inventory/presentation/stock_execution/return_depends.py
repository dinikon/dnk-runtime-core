from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.handler import (
    GetReturnExecutionResultHandler,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.return_result_repository import (
    SqlAlchemyReturnExecutionResultRepository,
)


def get_return_execution_result_handler(
    uow: UoWDep,
) -> GetReturnExecutionResultHandler:
    """Собирает чтение результата на tenant-сессии общего UoW."""
    return GetReturnExecutionResultHandler(
        SqlAlchemyReturnExecutionResultRepository(uow.session)
    )


GetReturnExecutionResultHandlerDep = Annotated[
    GetReturnExecutionResultHandler,
    Depends(get_return_execution_result_handler),
]
