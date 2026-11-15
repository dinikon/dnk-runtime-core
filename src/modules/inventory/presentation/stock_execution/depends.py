from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_query_repository import SqlAlchemyReceiptFactsQueryRepository
from src.modules.inventory.application.stock_execution.query.get_stock_execution.handler import GetStockExecutionHandler

def get_handler(uow:UoWDep)->GetStockExecutionHandler:
    """Собирает чтение факта через проекцию общей tenant-сессии."""
    return GetStockExecutionHandler(SqlAlchemyReceiptFactsQueryRepository(uow.session))
GetStockExecutionHandlerDep=Annotated[GetStockExecutionHandler,Depends(get_handler)]
