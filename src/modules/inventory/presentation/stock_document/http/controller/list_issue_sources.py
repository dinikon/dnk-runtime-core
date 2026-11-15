from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.inventory.presentation.stock_document.issue_depends import (
    ListIssueSourcesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_issue_sources import (
    ListIssueSourcesRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_issue_sources import (
    ListIssueSourcesResponse,
)
from src.modules.inventory.application.stock_document.query.list_issue_sources.query import (
    ListIssueSourcesQuery,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


async def list_issue_sources(
    document_id: UUID,
    request: Annotated[ListIssueSourcesRequest, Query()],
    handler: ListIssueSourcesHandlerDep,
) -> ListIssueSourcesResponse:
    """Преобразует HTTP-параметры в сценарий поиска физических источников."""
    try:
        result = await handler.execute(
            ListIssueSourcesQuery(
                document_id,
                request.document_line_id,
                request.search.strip() if request.search else None,
                request.offset,
                request.limit,
                request.position_id,
            )
        )
    except StockDocumentLineNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListIssueSourcesResponse.from_dto(result)
