from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_status_change_document.query import (
    GetStatusChangeDocumentQuery,
)
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    GetStatusChangeDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_status_change_document import (
    GetStatusChangeDocumentResponse,
)


async def get_status_change_document(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetStatusChangeDocumentHandlerDep,
) -> GetStatusChangeDocumentResponse:
    """Читает исторический план текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetStatusChangeDocumentQuery(document_id))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetStatusChangeDocumentResponse.from_dto(result)
