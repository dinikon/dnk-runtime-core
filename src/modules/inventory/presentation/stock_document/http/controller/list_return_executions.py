from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.query import (
    ListReturnExecutionsQuery,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    ListReturnExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_executions import (
    ListReturnExecutionsResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnFactNotFoundError,
)
from typing import Annotated
from fastapi import Query
from src.modules.inventory.presentation.stock_document.http.request.list_return_executions import (
    ListReturnExecutionsRequest,
)


async def list_return_executions(
    document_id: UUID,
    query: Annotated[ListReturnExecutionsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListReturnExecutionsHandlerDep,
) -> ListReturnExecutionsResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListReturnExecutionsQuery(document_id, query.offset, query.limit)
        )
    except (StockDocumentNotFoundError, ReturnFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListReturnExecutionsResponse.from_dto(result)
