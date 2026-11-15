from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.query import (
    ListWriteOffDocumentsQuery,
)
from src.modules.inventory.presentation.stock_document.write_off_depends import (
    ListWriteOffDocumentsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_write_off_documents import (
    ListWriteOffDocumentsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_write_off_documents import (
    ListWriteOffDocumentsResponse,
)


async def list_write_off_documents(
    query: Annotated[ListWriteOffDocumentsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListWriteOffDocumentsHandlerDep,
) -> ListWriteOffDocumentsResponse:
    """Передаёт проверенные фильтры в отдельный Query сценарий."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListWriteOffDocumentsQuery(
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
    return ListWriteOffDocumentsResponse.from_dto(result)
