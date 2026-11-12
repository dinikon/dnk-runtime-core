from fastapi import HTTPException, Query

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListQueryError,
)
from src.modules.inventory.presentation.warehouse.depends import (
    ListWarehousesHandlerDep,
)
from src.modules.inventory.presentation.warehouse.http.response.list_warehouses import (
    ListWarehousesResponse,
)


async def list_warehouses(
    context: AuthenticatedRequestContextDep,
    handler: ListWarehousesHandlerDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
) -> ListWarehousesResponse:
    """Преобразует фильтры HTTP в типизированный запрос страницы."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListWarehousesQuery(
                offset=offset, limit=limit, search=search, is_active=is_active
            )
        )
    except InvalidWarehouseListQueryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ListWarehousesResponse.from_dto(result)
