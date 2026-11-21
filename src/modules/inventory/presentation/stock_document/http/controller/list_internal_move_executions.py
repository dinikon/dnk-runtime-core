from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.query import (
    ListInternalMoveExecutionsQuery,
)
from src.modules.inventory.presentation.stock_document.internal_move_depends import (
    ListInternalMoveExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_executions import (
    ListInternalMoveExecutionsResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMoveFactNotFoundError,
)
from typing import Annotated
from fastapi import Query
from src.modules.inventory.presentation.stock_document.http.request.list_internal_move_executions import (
    ListInternalMoveExecutionsRequest,
)


async def list_internal_move_executions(
    document_id: UUID,
    query: Annotated[ListInternalMoveExecutionsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListInternalMoveExecutionsHandlerDep,
) -> ListInternalMoveExecutionsResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListInternalMoveExecutionsQuery(document_id, query.offset, query.limit)
        )
    except (StockDocumentNotFoundError, InternalMoveFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListInternalMoveExecutionsResponse.from_dto(result)
