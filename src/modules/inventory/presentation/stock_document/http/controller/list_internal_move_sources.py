from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.inventory.presentation.stock_document.internal_move_depends import (
    ListInternalMoveSourcesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_internal_move_sources import (
    ListInternalMoveSourcesRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_sources import (
    ListInternalMoveSourcesResponse,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.query import (
    ListInternalMoveSourcesQuery,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


async def list_internal_move_sources(
    document_id: UUID,
    request: Annotated[ListInternalMoveSourcesRequest, Query()],
    handler: ListInternalMoveSourcesHandlerDep,
) -> ListInternalMoveSourcesResponse:
    """Преобразует HTTP-параметры в сценарий поиска физических источников."""
    try:
        result = await handler.execute(
            ListInternalMoveSourcesQuery(
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
    return ListInternalMoveSourcesResponse.from_dto(result)
