from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.query import (
    GetStockExecutionDetailsQuery,
)
from src.modules.inventory.presentation.stock_execution.read_depends import (
    GetStockExecutionDetailsHandlerDep,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_stock_execution_details import (
    GetStockExecutionDetailsResponse,
)


async def get_stock_execution_details(
    identifier: UUID, handler: GetStockExecutionDetailsHandlerDep
) -> GetStockExecutionDetailsResponse:
    """Преобразует собственный HTTP-вход в Query и сериализует конкретный результат."""
    try:
        result = await handler.execute(GetStockExecutionDetailsQuery(identifier))
    except ReceiptFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockPositionVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return GetStockExecutionDetailsResponse.from_dto(result)
