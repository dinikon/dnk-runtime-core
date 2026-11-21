from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_write_off_executions.query import (
    ListWriteOffExecutionsQuery,
)
from src.modules.inventory.presentation.stock_document.write_off_depends import (
    ListWriteOffExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.list_write_off_executions import (
    ListWriteOffExecutionsResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.write_off_error import (
    WriteOffFactNotFoundError,
)
from typing import Annotated
from fastapi import Query
from src.modules.inventory.presentation.stock_document.http.request.list_write_off_executions import (
    ListWriteOffExecutionsRequest,
)


async def list_write_off_executions(
    document_id: UUID,
    query: Annotated[ListWriteOffExecutionsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListWriteOffExecutionsHandlerDep,
) -> ListWriteOffExecutionsResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListWriteOffExecutionsQuery(document_id, query.offset, query.limit)
        )
    except (StockDocumentNotFoundError, WriteOffFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListWriteOffExecutionsResponse.from_dto(result)
