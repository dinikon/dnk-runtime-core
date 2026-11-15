from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.query import (
    ListStatusChangeDocumentsQuery,
)
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    ListStatusChangeDocumentsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_status_change_documents import (
    ListStatusChangeDocumentsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_status_change_documents import (
    ListStatusChangeDocumentsResponse,
)


async def list_status_change_documents(
    query: Annotated[ListStatusChangeDocumentsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListStatusChangeDocumentsHandlerDep,
) -> ListStatusChangeDocumentsResponse:
    """Передаёт проверенные фильтры в отдельный Query сценарий."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListStatusChangeDocumentsQuery(
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
    return ListStatusChangeDocumentsResponse.from_dto(result)
