from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.prepare_internal_move.query import (
    PrepareInternalMoveQuery,
)
from src.modules.inventory.presentation.stock_document.internal_move_depends import (
    PrepareInternalMoveHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_internal_move import (
    PrepareInternalMoveResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMoveFactNotFoundError,
)


async def prepare_internal_move(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: PrepareInternalMoveHandlerDep,
) -> PrepareInternalMoveResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(PrepareInternalMoveQuery(document_id))
    except (StockDocumentNotFoundError, InternalMoveFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PrepareInternalMoveResponse.from_dto(result)
