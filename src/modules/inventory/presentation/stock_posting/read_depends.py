from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.presentation.stock_document.depends import (
    StockOwnerReferenceDep,
)
from src.modules.inventory.infrastructure.stock_posting.persistence.query_repository import (
    SqlAlchemyStockPostingQueryRepository,
)
from src.modules.inventory.application.stock_posting.query.list_stock_movements.handler import (
    ListStockMovementsHandler,
)


def get_list_stock_movements_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ListStockMovementsHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return ListStockMovementsHandler(
        SqlAlchemyStockPostingQueryRepository(uow.session), owners
    )


ListStockMovementsHandlerDep = Annotated[
    ListStockMovementsHandler, Depends(get_list_stock_movements_handler)
]
from src.modules.inventory.application.stock_posting.query.list_stock_postings.handler import (
    ListStockPostingsHandler,
)


def get_list_stock_postings_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ListStockPostingsHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return ListStockPostingsHandler(
        SqlAlchemyStockPostingQueryRepository(uow.session), owners
    )


ListStockPostingsHandlerDep = Annotated[
    ListStockPostingsHandler, Depends(get_list_stock_postings_handler)
]
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.handler import (
    GetStockPostingDetailsHandler,
)


def get_get_stock_posting_details_handler(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> GetStockPostingDetailsHandler:
    """Собирает чтение и публичное дополнение CRM на общей tenant-сессии."""
    return GetStockPostingDetailsHandler(
        SqlAlchemyStockPostingQueryRepository(uow.session), owners
    )


GetStockPostingDetailsHandlerDep = Annotated[
    GetStockPostingDetailsHandler, Depends(get_get_stock_posting_details_handler)
]
