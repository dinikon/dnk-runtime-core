from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_query_repository import (
    SqlAlchemyReceiptFactsQueryRepository,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting.handler import (
    GetStockPostingHandler,
)


def get_handler(uow: UoWDep) -> GetStockPostingHandler:
    """Собирает чтение факта через проекцию общей tenant-сессии."""
    return GetStockPostingHandler(SqlAlchemyReceiptFactsQueryRepository(uow.session))


GetStockPostingHandlerDep = Annotated[GetStockPostingHandler, Depends(get_handler)]
