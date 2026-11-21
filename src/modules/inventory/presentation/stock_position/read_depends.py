from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.presentation.stock_document.depends import (
    StockOwnerReferenceDep,
)
from src.modules.inventory.infrastructure.stock_position.persistence.query_repository import (
    SqlAlchemyStockPositionQueryRepository,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.handler import (
    ListStockPositionsHandler,
)


def get_list_stock_positions_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ListStockPositionsHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return ListStockPositionsHandler(
        SqlAlchemyStockPositionQueryRepository(uow.session), owners
    )


ListStockPositionsHandlerDep = Annotated[
    ListStockPositionsHandler, Depends(get_list_stock_positions_handler)
]
from src.modules.inventory.application.stock_position.query.get_stock_position.handler import (
    GetStockPositionHandler,
)


def get_get_stock_position_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> GetStockPositionHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return GetStockPositionHandler(
        SqlAlchemyStockPositionQueryRepository(uow.session), owners
    )


GetStockPositionHandlerDep = Annotated[
    GetStockPositionHandler, Depends(get_get_stock_position_handler)
]

from src.modules.inventory.application.stock_position.query.list_stock_balances.handler import (
    ListStockBalancesHandler,
)


def get_list_stock_balances_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ListStockBalancesHandler:
    """Собирает собственную сводку на общей tenant-сессии и публичном CRM-порте."""
    return ListStockBalancesHandler(
        SqlAlchemyStockPositionQueryRepository(uow.session), owners
    )


ListStockBalancesHandlerDep = Annotated[
    ListStockBalancesHandler, Depends(get_list_stock_balances_handler)
]
