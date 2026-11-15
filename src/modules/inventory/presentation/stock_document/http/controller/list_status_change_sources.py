from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    ListStatusChangeSourcesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_status_change_sources import (
    ListStatusChangeSourcesRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_status_change_sources import (
    ListStatusChangeSourcesResponse,
)
from src.modules.inventory.application.stock_document.query.list_status_change_sources.query import (
    ListStatusChangeSourcesQuery,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


async def list_status_change_sources(
    document_id: UUID,
    request: Annotated[ListStatusChangeSourcesRequest, Query()],
    handler: ListStatusChangeSourcesHandlerDep,
) -> ListStatusChangeSourcesResponse:
    """Преобразует HTTP-параметры в сценарий поиска физических источников."""
    try:
        result = await handler.execute(
            ListStatusChangeSourcesQuery(
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
    return ListStatusChangeSourcesResponse.from_dto(result)
