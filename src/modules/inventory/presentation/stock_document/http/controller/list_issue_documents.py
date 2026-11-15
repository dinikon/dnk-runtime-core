from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.query import (
    ListIssueDocumentsQuery,
)
from src.modules.inventory.presentation.stock_document.issue_depends import (
    ListIssueDocumentsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_issue_documents import (
    ListIssueDocumentsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_issue_documents import (
    ListIssueDocumentsResponse,
)


async def list_issue_documents(
    query: Annotated[ListIssueDocumentsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListIssueDocumentsHandlerDep,
) -> ListIssueDocumentsResponse:
    """Передаёт проверенные фильтры в отдельный Query сценарий."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListIssueDocumentsQuery(
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
    return ListIssueDocumentsResponse.from_dto(result)
