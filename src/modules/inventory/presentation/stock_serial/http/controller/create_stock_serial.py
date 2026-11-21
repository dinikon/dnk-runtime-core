from uuid import UUID
from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_serial.command.create_stock_serial.command import (
    CreateStockSerialCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    StockSerialNumberAlreadyExistsError,
)
from src.modules.inventory.presentation.stock_serial.depends import (
    CreateStockSerialHandlerDep,
)
from src.modules.inventory.presentation.stock_serial.http.request.create_stock_serial import (
    CreateStockSerialRequest,
)
from src.modules.inventory.presentation.stock_serial.http.response.create_stock_serial import (
    CreateStockSerialResponse,
)


async def create_stock_serial(
    inventory_item_id: UUID,
    payload: CreateStockSerialRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateStockSerialHandlerDep,
) -> CreateStockSerialResponse:
    """Создаёт экземпляр выбранного SKU, переводя ожидаемые предметные ошибки в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateStockSerialCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                number=payload.number,
                lot_id=(
                    StockLotIdVO.from_value(payload.lot_id)
                    if payload.lot_id is not None
                    else None
                ),
            )
        )
    except (InventoryItemNotFoundError, StockLotNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockSerialNumberAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateStockSerialResponse.from_dto(result)
