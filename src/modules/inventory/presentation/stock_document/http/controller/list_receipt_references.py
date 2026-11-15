from typing import Annotated
from uuid import UUID
from fastapi import Query,HTTPException
from src.modules.identity.presentation.auth.depends import AuthenticatedRequestContextDep
from src.modules.inventory.application.stock_document.query.list_receipt_references.query import ListReceiptReferencesQuery
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.presentation.stock_document.depends import ListReceiptReferencesHandlerDep
from src.modules.inventory.presentation.stock_document.http.request.list_receipt_references import ListReceiptReferencesRequest
from src.modules.inventory.presentation.stock_document.http.response.list_receipt_references import ListReceiptReferencesResponse
async def list_receipt_references(document_id:UUID,query:Annotated[ListReceiptReferencesRequest,Query()],context:AuthenticatedRequestContextDep,handler:ListReceiptReferencesHandlerDep)->ListReceiptReferencesResponse:
    """Преобразует проверенный поиск в конкретный query текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:raise HTTPException(403,"Tenant context is required.")
    try:result=await handler.execute(ListReceiptReferencesQuery(document_id,query.kind,query.document_line_id,query.lot_id,query.search.strip() or None if query.search else None,query.offset,query.limit))
    except StockDocumentNotFoundError as exc:raise HTTPException(404,str(exc)) from exc
    return ListReceiptReferencesResponse.from_dto(result)
