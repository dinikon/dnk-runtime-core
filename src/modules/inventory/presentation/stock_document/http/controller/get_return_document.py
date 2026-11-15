from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    GetReturnDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_return_document import (
    GetReturnDocumentResponse,
)


async def get_return_document(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetReturnDocumentHandlerDep,
) -> GetReturnDocumentResponse:
    """Читает исторический план текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetReturnDocumentQuery(document_id))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetReturnDocumentResponse.from_dto(result)
