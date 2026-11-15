from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.prepare_issue.query import (
    PrepareIssueQuery,
)
from src.modules.inventory.presentation.stock_document.issue_depends import (
    PrepareIssueHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_issue import (
    PrepareIssueResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.issue_error import (
    IssueFactNotFoundError,
)


async def prepare_issue(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: PrepareIssueHandlerDep,
) -> PrepareIssueResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(PrepareIssueQuery(document_id))
    except (StockDocumentNotFoundError, IssueFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PrepareIssueResponse.from_dto(result)
