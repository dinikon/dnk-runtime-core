from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.query import (
    ListReceiptExecutionsQuery,
)
from src.modules.inventory.presentation.stock_document.depends import (
    ListReceiptExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.list_receipt_executions import (
    ListReceiptExecutionsResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from typing import Annotated
from fastapi import Query
from src.modules.inventory.presentation.stock_document.http.request.list_receipt_executions import (
    ListReceiptExecutionsRequest,
)


async def list_receipt_executions(
    document_id: UUID,
    query: Annotated[ListReceiptExecutionsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListReceiptExecutionsHandlerDep,
) -> ListReceiptExecutionsResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListReceiptExecutionsQuery(document_id, query.offset, query.limit)
        )
    except (StockDocumentNotFoundError, ReceiptFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListReceiptExecutionsResponse.from_dto(result)
