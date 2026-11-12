from fastapi import HTTPException, Query

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.error import (
    InvalidInventoryItemListQueryError,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.query import (
    ListInventoryItemsQuery,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    ListInventoryItemsHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.response.list_inventory_items import (
    ListInventoryItemsResponse,
)


async def list_inventory_items(
    context: AuthenticatedRequestContextDep,
    handler: ListInventoryItemsHandlerDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
) -> ListInventoryItemsResponse:
    """Переводит query-параметры в Application-запрос списка текущего tenant."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListInventoryItemsQuery(offset=offset, limit=limit, search=search)
        )
    except InvalidInventoryItemListQueryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ListInventoryItemsResponse.from_dto(result)
