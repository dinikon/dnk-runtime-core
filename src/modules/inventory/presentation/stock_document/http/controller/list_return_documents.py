from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.query import (
    ListReturnDocumentsQuery,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    ListReturnDocumentsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_return_documents import (
    ListReturnDocumentsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_documents import (
    ListReturnDocumentsResponse,
)


async def list_return_documents(
    query: Annotated[ListReturnDocumentsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListReturnDocumentsHandlerDep,
) -> ListReturnDocumentsResponse:
    """Передаёт проверенные фильтры в отдельный Query сценарий."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListReturnDocumentsQuery(
            origin_execution_id=query.origin_execution_id,
            search=query.search.strip() or None if query.search is not None else None,
            warehouse_id=query.warehouse_id,
            owner_id=query.owner_id,
            status=None if query.status == "ALL" else query.status,
            created_from=query.created_from,
            created_to=query.created_to,
            offset=query.offset,
            limit=query.limit,
        )
    )
    return ListReturnDocumentsResponse.from_dto(result)
