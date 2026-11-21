from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.query import (
    ListStockSerialsQuery,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.presentation.stock_serial.depends import (
    ListStockSerialsHandlerDep,
)
from src.modules.inventory.presentation.stock_serial.http.request.list_stock_serials import (
    ListStockSerialsRequest,
)
from src.modules.inventory.presentation.stock_serial.http.response.list_stock_serials import (
    ListStockSerialsResponse,
)


async def list_stock_serials(
    inventory_item_id: UUID,
    params: Annotated[ListStockSerialsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListStockSerialsHandlerDep,
) -> ListStockSerialsResponse:
    """Читает страницу существующего SKU без проверки его текущего режима учёта."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListStockSerialsQuery(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                offset=params.offset,
                limit=params.limit,
                search=params.search,
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListStockSerialsResponse.from_dto(result)
