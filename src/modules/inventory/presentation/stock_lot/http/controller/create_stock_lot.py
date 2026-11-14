from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_lot.command.create_stock_lot.command import (
    CreateStockLotCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.error import (
    StockLotNumberAlreadyExistsError,
)
from src.modules.inventory.presentation.stock_lot.depends import (
    CreateStockLotHandlerDep,
)
from src.modules.inventory.presentation.stock_lot.http.request.create_stock_lot import (
    CreateStockLotRequest,
)
from src.modules.inventory.presentation.stock_lot.http.response.create_stock_lot import (
    CreateStockLotResponse,
)


async def create_stock_lot(
    inventory_item_id: UUID,
    payload: CreateStockLotRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateStockLotHandlerDep,
) -> CreateStockLotResponse:
    """Создаёт партию выбранного SKU, переводя ожидаемые предметные ошибки в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateStockLotCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                number=payload.number,
                manufactured_on=payload.manufactured_on,
                expires_on=payload.expires_on,
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockLotNumberAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateStockLotResponse.from_dto(result)
