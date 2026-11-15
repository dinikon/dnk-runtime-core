from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.query import (
    ListStatusChangeExecutionsQuery,
)
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    ListStatusChangeExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.list_status_change_executions import (
    ListStatusChangeExecutionsResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.status_change_error import (
    StatusChangeFactNotFoundError,
)
from typing import Annotated
from fastapi import Query
from src.modules.inventory.presentation.stock_document.http.request.list_status_change_executions import (
    ListStatusChangeExecutionsRequest,
)


async def list_status_change_executions(
    document_id: UUID,
    query: Annotated[ListStatusChangeExecutionsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListStatusChangeExecutionsHandlerDep,
) -> ListStatusChangeExecutionsResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListStatusChangeExecutionsQuery(document_id, query.offset, query.limit)
        )
    except (StockDocumentNotFoundError, StatusChangeFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListStatusChangeExecutionsResponse.from_dto(result)
