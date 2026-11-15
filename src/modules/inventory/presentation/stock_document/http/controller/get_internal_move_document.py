from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_internal_move_document.query import (
    GetInternalMoveDocumentQuery,
)
from src.modules.inventory.presentation.stock_document.internal_move_depends import (
    GetInternalMoveDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_internal_move_document import (
    GetInternalMoveDocumentResponse,
)


async def get_internal_move_document(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetInternalMoveDocumentHandlerDep,
) -> GetInternalMoveDocumentResponse:
    """Читает исторический план текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetInternalMoveDocumentQuery(document_id))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetInternalMoveDocumentResponse.from_dto(result)
