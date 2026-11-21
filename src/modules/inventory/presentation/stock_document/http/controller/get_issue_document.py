from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_issue_document.query import (
    GetIssueDocumentQuery,
)
from src.modules.inventory.presentation.stock_document.issue_depends import (
    GetIssueDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_issue_document import (
    GetIssueDocumentResponse,
)


async def get_issue_document(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetIssueDocumentHandlerDep,
) -> GetIssueDocumentResponse:
    """Читает исторический план текущего tenant."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetIssueDocumentQuery(document_id))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetIssueDocumentResponse.from_dto(result)
