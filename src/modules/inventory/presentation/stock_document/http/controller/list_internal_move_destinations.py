from typing import Annotated
from uuid import UUID
from fastapi import Query, HTTPException
from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.query import (
    ListInternalMoveDestinationsQuery,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.presentation.stock_document.internal_move_depends import (
    ListInternalMoveDestinationsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_internal_move_destinations import (
    ListInternalMoveDestinationsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_destinations import (
    ListInternalMoveDestinationsResponse,
)


async def list_internal_move_destinations(
    document_id: UUID,
    request: Annotated[ListInternalMoveDestinationsRequest, Query()],
    handler: ListInternalMoveDestinationsHandlerDep,
) -> ListInternalMoveDestinationsResponse:
    """Преобразует параметры поиска адресов и ожидаемую ошибку отсутствия документа."""
    try:
        result = await handler.execute(
            ListInternalMoveDestinationsQuery(
                document_id,
                request.search.strip() if request.search else None,
                request.offset,
                request.limit,
                request.location_id,
            )
        )
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListInternalMoveDestinationsResponse.from_dto(result)
