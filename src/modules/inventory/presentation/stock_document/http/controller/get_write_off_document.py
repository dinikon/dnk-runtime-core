from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
)
from src.modules.inventory.presentation.stock_document.write_off_depends import (
    GetWriteOffDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_write_off_document import (
    GetWriteOffDocumentResponse,
)


async def get_write_off_document(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetWriteOffDocumentHandlerDep,
) -> GetWriteOffDocumentResponse:
    """Читает исторический план текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetWriteOffDocumentQuery(document_id))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetWriteOffDocumentResponse.from_dto(result)
