from uuid import UUID
from fastapi import HTTPException

from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_serial.command.update_stock_serial.command import (
    UpdateStockSerialCommand,
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
    UpdateStockSerialHandlerDep,
)
from src.modules.inventory.presentation.stock_serial.http.request.put_stock_serial import (
    PutStockSerialRequest,
)
from src.modules.inventory.presentation.stock_serial.http.response.put_stock_serial import (
    PutStockSerialResponse,
)


async def put_stock_serial(
    inventory_item_id: UUID,
    serial_id: UUID,
    payload: PutStockSerialRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateStockSerialHandlerDep,
) -> PutStockSerialResponse:
    """Применяет PUT идентификации и возвращает карточку с актуальными датами партии."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateStockSerialCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                serial_id=StockSerialIdVO.from_value(serial_id),
                fields=frozenset({"number", "lot_id"}),
                number=payload.number,
                lot_id=(
                    StockLotIdVO.from_value(payload.lot_id)
                    if payload.lot_id is not None
                    else None
                ),
            )
        )
    except (
        InventoryItemNotFoundError,
        StockLotNotFoundError,
        StockSerialNotFoundError,
    ) as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockSerialNumberAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutStockSerialResponse.from_dto(result)
