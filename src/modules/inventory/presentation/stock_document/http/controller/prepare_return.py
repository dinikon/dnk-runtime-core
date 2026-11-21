from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.prepare_return.query import (
    PrepareReturnQuery,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    PrepareReturnHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_return import (
    PrepareReturnResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnFactNotFoundError,
)


async def prepare_return(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: PrepareReturnHandlerDep,
) -> PrepareReturnResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(PrepareReturnQuery(document_id))
    except (StockDocumentNotFoundError, ReturnFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PrepareReturnResponse.from_dto(result)
