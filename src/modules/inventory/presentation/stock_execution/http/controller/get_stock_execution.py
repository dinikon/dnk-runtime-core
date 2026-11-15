from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import AuthenticatedRequestContextDep
from src.modules.inventory.application.stock_execution.query.get_stock_execution.query import GetStockExecutionQuery
from src.modules.inventory.presentation.stock_execution.depends import GetStockExecutionHandlerDep
from src.modules.inventory.presentation.stock_execution.http.response.get_stock_execution import GetStockExecutionResponse
from src.modules.inventory.domain.stock_document.receipt_error import ReceiptFactNotFoundError
async def get_stock_execution(identifier:UUID,context:AuthenticatedRequestContextDep,handler:GetStockExecutionHandlerDep)->GetStockExecutionResponse:
    """Возвращает неизменяемую карточку факта без изменения текущих остатков."""
    if context.principal is None or context.principal.tenant_id is None:raise HTTPException(403,"Tenant context is required.")
    try:result=await handler.execute(GetStockExecutionQuery(identifier))
    except ReceiptFactNotFoundError as exc:raise HTTPException(404,str(exc)) from exc
    return GetStockExecutionResponse.from_dto(result)
