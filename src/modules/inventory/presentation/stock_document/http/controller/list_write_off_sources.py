from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.inventory.presentation.stock_document.write_off_depends import (
    ListWriteOffSourcesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_write_off_sources import (
    ListWriteOffSourcesRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_write_off_sources import (
    ListWriteOffSourcesResponse,
)
from src.modules.inventory.application.stock_document.query.list_write_off_sources.query import (
    ListWriteOffSourcesQuery,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


async def list_write_off_sources(
    document_id: UUID,
    request: Annotated[ListWriteOffSourcesRequest, Query()],
    handler: ListWriteOffSourcesHandlerDep,
) -> ListWriteOffSourcesResponse:
    """Преобразует HTTP-параметры в сценарий поиска физических источников."""
    try:
        result = await handler.execute(
            ListWriteOffSourcesQuery(
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
    return ListWriteOffSourcesResponse.from_dto(result)
