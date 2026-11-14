from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_lot.command.update_stock_lot.command import (
    UpdateStockLotCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.presentation.stock_lot.depends import (
    UpdateStockLotHandlerDep,
)
from src.modules.inventory.presentation.stock_lot.http.request.put_stock_lot import (
    PutStockLotRequest,
)
from src.modules.inventory.presentation.stock_lot.http.response.put_stock_lot import (
    PutStockLotResponse,
)


async def put_stock_lot(
    inventory_item_id: UUID,
    lot_id: UUID,
    payload: PutStockLotRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateStockLotHandlerDep,
) -> PutStockLotResponse:
    """Преобразует PUT дат в команду и возвращает подтверждённую карточку партии."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateStockLotCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                lot_id=StockLotIdVO.from_value(lot_id),
                fields=frozenset({"manufactured_on", "expires_on"}),
                manufactured_on=payload.manufactured_on,
                expires_on=payload.expires_on,
            )
        )
    except (InventoryItemNotFoundError, StockLotNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutStockLotResponse.from_dto(result)
