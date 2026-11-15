from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_receipt_document.query import (
    GetReceiptDocumentQuery,
)
from src.modules.inventory.presentation.stock_document.depends import (
    GetReceiptDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_receipt_document import (
    GetReceiptDocumentResponse,
)


async def get_receipt_document(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetReceiptDocumentHandlerDep,
) -> GetReceiptDocumentResponse:
    """Читает исторический план текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetReceiptDocumentQuery(document_id))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetReceiptDocumentResponse.from_dto(result)
