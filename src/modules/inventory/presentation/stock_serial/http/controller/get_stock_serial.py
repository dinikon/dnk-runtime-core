from uuid import UUID
from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.query import (
    GetStockSerialQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.presentation.stock_serial.depends import (
    GetStockSerialHandlerDep,
)
from src.modules.inventory.presentation.stock_serial.http.response.get_stock_serial import (
    GetStockSerialResponse,
)


async def get_stock_serial(
    inventory_item_id: UUID,
    serial_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetStockSerialHandlerDep,
) -> GetStockSerialResponse:
    """Читает карточку по паре ID, не раскрывая экземпляра другого владельца."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetStockSerialQuery(
                InventoryItemIdVO.from_value(inventory_item_id),
                StockSerialIdVO.from_value(serial_id),
            )
        )
    except StockSerialNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetStockSerialResponse.from_dto(result)
