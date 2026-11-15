from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.inventory.presentation.stock_document.return_depends import (
    ListReturnSourcesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_return_sources import (
    ListReturnSourcesRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_sources import (
    ListReturnSourcesResponse,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.query import (
    ListReturnSourcesQuery,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


async def list_return_sources(
    document_id: UUID,
    request: Annotated[ListReturnSourcesRequest, Query()],
    handler: ListReturnSourcesHandlerDep,
) -> ListReturnSourcesResponse:
    """Преобразует HTTP-параметры в сценарий поиска физических источников."""
    try:
        result = await handler.execute(
            ListReturnSourcesQuery(
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
    return ListReturnSourcesResponse.from_dto(result)
