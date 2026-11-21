from typing import Annotated
from uuid import UUID
from fastapi import Query, HTTPException
from src.modules.inventory.application.stock_document.query.list_return_destinations.query import (
    ListReturnDestinationsQuery,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.presentation.stock_document.return_depends import (
    ListReturnDestinationsHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.list_return_destinations import (
    ListReturnDestinationsRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_destinations import (
    ListReturnDestinationsResponse,
)


async def list_return_destinations(
    document_id: UUID,
    request: Annotated[ListReturnDestinationsRequest, Query()],
    handler: ListReturnDestinationsHandlerDep,
) -> ListReturnDestinationsResponse:
    """Преобразует параметры поиска адресов и ожидаемую ошибку отсутствия документа."""
    try:
        result = await handler.execute(
            ListReturnDestinationsQuery(
                document_id,
                request.search.strip() if request.search else None,
                request.offset,
                request.limit,
                request.location_id,
            )
        )
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListReturnDestinationsResponse.from_dto(result)
