from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.inventory.application.accounting.filters import StockAccountingFilters
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.query import (
    ListStockPositionsQuery,
)
from src.modules.inventory.presentation.stock_position.read_depends import (
    ListStockPositionsHandlerDep,
)
from src.modules.inventory.presentation.stock_position.http.response.list_stock_positions import (
    ListStockPositionsResponse,
)
from src.modules.inventory.presentation.stock_position.http.request.list_stock_positions import (
    ListStockPositionsRequest,
)


async def list_stock_positions(
    params: Annotated[ListStockPositionsRequest, Query()],
    handler: ListStockPositionsHandlerDep,
) -> ListStockPositionsResponse:
    """Преобразует собственный HTTP-вход в Query и сериализует конкретный результат."""
    try:
        result = await handler.execute(
            ListStockPositionsQuery(
                filters=StockAccountingFilters(
                    warehouse_id=params.warehouse_id,
                    location_id=params.location_id,
                    owner_id=params.owner_id,
                    inventory_item_id=params.inventory_item_id,
                    lot_id=params.lot_id,
                    serial_id=params.serial_id,
                    position_id=params.position_id,
                    stock_status=params.stock_status,
                    search=params.search,
                ),
                offset=params.offset,
                limit=params.limit,
                include_zero=params.include_zero,
            )
        )
    except ReceiptFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockPositionVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return ListStockPositionsResponse.from_dto(result)
