from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Query

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.query import (
    ListStockLotsQuery,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.presentation.stock_lot.depends import ListStockLotsHandlerDep
from src.modules.inventory.presentation.stock_lot.http.request.list_stock_lots import (
    ListStockLotsRequest,
)
from src.modules.inventory.presentation.stock_lot.http.response.list_stock_lots import (
    ListStockLotsResponse,
)


async def list_stock_lots(
    inventory_item_id: UUID,
    params: Annotated[ListStockLotsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListStockLotsHandlerDep,
) -> ListStockLotsResponse:
    """Читает страницу существующего SKU без проверки его текущего режима учёта."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListStockLotsQuery(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                offset=params.offset,
                limit=params.limit,
                search=params.search,
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListStockLotsResponse.from_dto(result)
