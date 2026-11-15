from typing import Annotated
from fastapi import Query, HTTPException
from src.modules.inventory.application.accounting.filters import StockAccountingFilters
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.application.stock_execution.query.list_stock_executions.query import (
    ListStockExecutionsQuery,
)
from src.modules.inventory.presentation.stock_execution.read_depends import (
    ListStockExecutionsHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.list_stock_executions import (
    ListStockExecutionsResponse,
)
from src.modules.inventory.presentation.stock_execution.http.request.list_stock_executions import (
    ListStockExecutionsRequest,
)


async def list_stock_executions(
    params: Annotated[ListStockExecutionsRequest, Query()],
    handler: ListStockExecutionsHandlerDep,
) -> ListStockExecutionsResponse:
    """Преобразует собственный HTTP-вход в Query и сериализует конкретный результат."""
    try:
        result = await handler.execute(
            ListStockExecutionsQuery(
                filters=StockAccountingFilters(
                    warehouse_id=params.warehouse_id,
                    location_id=params.location_id,
                    owner_id=params.owner_id,
                    inventory_item_id=params.inventory_item_id,
                    lot_id=params.lot_id,
                    serial_id=params.serial_id,
                    position_id=params.position_id,
                    document_id=params.document_id,
                    execution_id=params.execution_id,
                    posting_id=params.posting_id,
                    stock_status=params.stock_status,
                    operation_type=params.operation_type,
                    posted_from=params.posted_from,
                    posted_to=params.posted_to,
                    search=params.search,
                ),
                offset=params.offset,
                limit=params.limit,
            )
        )
    except ReceiptFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockPositionVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return ListStockExecutionsResponse.from_dto(result)
