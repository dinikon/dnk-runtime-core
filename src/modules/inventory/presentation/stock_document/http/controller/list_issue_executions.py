from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_issue_executions.query import (
    ListIssueExecutionsQuery,
)
from src.modules.inventory.presentation.stock_document.issue_depends import (
    ListIssueExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.list_issue_executions import (
    ListIssueExecutionsResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.issue_error import (
    IssueFactNotFoundError,
)
from typing import Annotated
from fastapi import Query
from src.modules.inventory.presentation.stock_document.http.request.list_issue_executions import (
    ListIssueExecutionsRequest,
)


async def list_issue_executions(
    document_id: UUID,
    query: Annotated[ListIssueExecutionsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListIssueExecutionsHandlerDep,
) -> ListIssueExecutionsResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListIssueExecutionsQuery(document_id, query.offset, query.limit)
        )
    except (StockDocumentNotFoundError, IssueFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListIssueExecutionsResponse.from_dto(result)
