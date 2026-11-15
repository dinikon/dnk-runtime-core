from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import AuthenticatedRequestContextDep
from src.modules.inventory.application.stock_posting.query.get_stock_posting.query import GetStockPostingQuery
from src.modules.inventory.presentation.stock_posting.depends import GetStockPostingHandlerDep
from src.modules.inventory.presentation.stock_posting.http.response.get_stock_posting import GetStockPostingResponse
from src.modules.inventory.domain.stock_document.receipt_error import ReceiptFactNotFoundError
async def get_stock_posting(identifier:UUID,context:AuthenticatedRequestContextDep,handler:GetStockPostingHandlerDep)->GetStockPostingResponse:
    """Возвращает неизменяемую карточку факта без изменения текущих остатков."""
    if context.principal is None or context.principal.tenant_id is None:raise HTTPException(403,"Tenant context is required.")
    try:result=await handler.execute(GetStockPostingQuery(identifier))
    except ReceiptFactNotFoundError as exc:raise HTTPException(404,str(exc)) from exc
    return GetStockPostingResponse.from_dto(result)
