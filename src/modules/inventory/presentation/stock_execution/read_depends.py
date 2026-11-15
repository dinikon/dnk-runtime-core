from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.presentation.stock_document.depends import (
    StockOwnerReferenceDep,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.query_repository import (
    SqlAlchemyStockExecutionQueryRepository,
)
from src.modules.inventory.application.stock_execution.query.list_stock_executions.handler import (
    ListStockExecutionsHandler,
)


def get_list_stock_executions_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ListStockExecutionsHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return ListStockExecutionsHandler(
        SqlAlchemyStockExecutionQueryRepository(uow.session), owners
    )


ListStockExecutionsHandlerDep = Annotated[
    ListStockExecutionsHandler, Depends(get_list_stock_executions_handler)
]
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.handler import (
    GetStockExecutionDetailsHandler,
)


def get_get_stock_execution_details_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> GetStockExecutionDetailsHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return GetStockExecutionDetailsHandler(
        SqlAlchemyStockExecutionQueryRepository(uow.session), owners
    )


GetStockExecutionDetailsHandlerDep = Annotated[
    GetStockExecutionDetailsHandler, Depends(get_get_stock_execution_details_handler)
]
