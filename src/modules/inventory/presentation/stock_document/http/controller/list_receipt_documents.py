from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.query import (
    ListReceiptDocumentsQuery,
)
from src.modules.inventory.presentation.stock_document.depends import (
    ListReceiptDocumentsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_receipt_documents import (
    ListReceiptDocumentsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_receipt_documents import (
    ListReceiptDocumentsResponse,
)


async def list_receipt_documents(
    query: Annotated[ListReceiptDocumentsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListReceiptDocumentsHandlerDep,
) -> ListReceiptDocumentsResponse:
    """Передаёт проверенные фильтры в отдельный Query сценарий."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListReceiptDocumentsQuery(
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
    return ListReceiptDocumentsResponse.from_dto(result)
