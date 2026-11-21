from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.query import (
    GetStockPositionQuery,
)
from src.modules.inventory.presentation.stock_position.read_depends import (
    GetStockPositionHandlerDep,
)
from src.modules.inventory.presentation.stock_position.http.response.get_stock_position import (
    GetStockPositionResponse,
)


async def get_stock_position(
    identifier: UUID, handler: GetStockPositionHandlerDep
) -> GetStockPositionResponse:
    """Преобразует собственный HTTP-вход в Query и сериализует конкретный результат."""
    try:
        result = await handler.execute(GetStockPositionQuery(identifier))
    except ReceiptFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockPositionVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return GetStockPositionResponse.from_dto(result)
