from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.application.stock_execution.query.get_write_off_execution_result.handler import (
    GetWriteOffExecutionResultHandler,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.write_off_result_repository import (
    SqlAlchemyWriteOffExecutionResultRepository,
)


def get_write_off_execution_result_handler(
    uow: UoWDep,
) -> GetWriteOffExecutionResultHandler:
    """Собирает чтение результата на tenant-сессии общего UoW."""
    return GetWriteOffExecutionResultHandler(
        SqlAlchemyWriteOffExecutionResultRepository(uow.session)
    )


GetWriteOffExecutionResultHandlerDep = Annotated[
    GetWriteOffExecutionResultHandler, Depends(get_write_off_execution_result_handler)
]
