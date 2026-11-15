from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.prepare_status_change.query import (
    PrepareStatusChangeQuery,
)
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    PrepareStatusChangeHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_status_change import (
    PrepareStatusChangeResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.status_change_error import (
    StatusChangeFactNotFoundError,
)


async def prepare_status_change(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: PrepareStatusChangeHandlerDep,
) -> PrepareStatusChangeResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(PrepareStatusChangeQuery(document_id))
    except (StockDocumentNotFoundError, StatusChangeFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PrepareStatusChangeResponse.from_dto(result)
