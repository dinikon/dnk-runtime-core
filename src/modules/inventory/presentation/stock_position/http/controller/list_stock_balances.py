from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.inventory.application.accounting.filters import StockAccountingFilters
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.application.stock_position.query.list_stock_balances.query import (
    ListStockBalancesQuery,
)
from src.modules.inventory.presentation.stock_position.read_depends import (
    ListStockBalancesHandlerDep,
)
from src.modules.inventory.presentation.stock_position.http.response.list_stock_balances import (
    ListStockBalancesResponse,
)
from src.modules.inventory.presentation.stock_position.http.request.list_stock_balances import (
    ListStockBalancesRequest,
)


async def list_stock_balances(
    params: Annotated[ListStockBalancesRequest, Query()],
    handler: ListStockBalancesHandlerDep,
) -> ListStockBalancesResponse:
    """Преобразует собственный HTTP-вход в Query и сериализует конкретный результат."""
    try:
        result = await handler.execute(
            ListStockBalancesQuery(
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
                group_by_lot=params.group_by_lot,
                group_by_serial=params.group_by_serial,
            )
        )
    except ReceiptFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockPositionVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return ListStockBalancesResponse.from_dto(result)
