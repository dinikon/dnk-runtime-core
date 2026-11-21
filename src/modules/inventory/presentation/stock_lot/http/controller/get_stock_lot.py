from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.query import (
    GetStockLotQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.presentation.stock_lot.depends import GetStockLotHandlerDep
from src.modules.inventory.presentation.stock_lot.http.response.get_stock_lot import (
    GetStockLotResponse,
)


async def get_stock_lot(
    inventory_item_id: UUID,
    lot_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetStockLotHandlerDep,
) -> GetStockLotResponse:
    """Читает карточку по паре ID, не раскрывая партии другого владельца."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetStockLotQuery(
                InventoryItemIdVO.from_value(inventory_item_id),
                StockLotIdVO.from_value(lot_id),
            )
        )
    except StockLotNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetStockLotResponse.from_dto(result)
