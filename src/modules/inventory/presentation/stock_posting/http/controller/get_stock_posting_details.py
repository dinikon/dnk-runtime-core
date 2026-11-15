from uuid import UUID
from fastapi import HTTPException
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.query import (
    GetStockPostingDetailsQuery,
)
from src.modules.inventory.presentation.stock_posting.read_depends import (
    GetStockPostingDetailsHandlerDep,
)
from src.modules.inventory.presentation.stock_posting.http.response.get_stock_posting_details import (
    GetStockPostingDetailsResponse,
)


async def get_stock_posting_details(
    identifier: UUID, handler: GetStockPostingDetailsHandlerDep
) -> GetStockPostingDetailsResponse:
    """Преобразует собственный HTTP-вход в Query и сериализует конкретный результат."""
    try:
        result = await handler.execute(GetStockPostingDetailsQuery(identifier))
    except ReceiptFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockPositionVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return GetStockPostingDetailsResponse.from_dto(result)
